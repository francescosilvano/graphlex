"""
Main module for collecting and analyzing Bluesky posts (packaged)
Provides `main()` entry point for console script.
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from itertools import combinations

import matplotlib.pyplot as plt
import pandas as pd
from atproto import Client, models
from atproto_client.exceptions import UnauthorizedError
from textblob import TextBlob

# --- IMPORT SHARED CONFIGURATION ---
from .config import (
    ANALYSIS_CONFIGS,
    KEYWORDS,
    HANDLE,
    PASSWORD,
    DATE_START as DEFAULT_DATE_START,
    DATE_END as DEFAULT_DATE_END,
    OUTPUT_DIR as DEFAULT_OUTPUT_DIR,
    LOCATION_KEYWORDS as DEFAULT_LOCATION_KEYWORDS,
    MAIN_KEYWORDS,
    GROUP_KEYWORDS,
    EXTRA_KEYWORDS,
    ARCHIVE_ENABLED,
    ARCHIVE_DIR
)
from .archive import RunArchive

# Initialize mutable configuration variables
DATE_START = DEFAULT_DATE_START
DATE_END = DEFAULT_DATE_END
OUTPUT_DIR = DEFAULT_OUTPUT_DIR
LOCATION_KEYWORDS = DEFAULT_LOCATION_KEYWORDS.copy()
VERBOSE_ENABLED = False
BLUE = "\033[94m"
RESET = "\033[0m"


class ProgressIndicator:
    """Render one compact animated status line for long-running operations."""

    def __init__(self, verbose=False):
        self._frames = "|/-\\"
        self._frame = 0
        self._message = ""
        self._running = False
        self._thread = None
        self._interactive = sys.stdout.isatty()
        self._verbose = verbose
        self._input_thread = None
        self._input_running = False
        self._output_lock = threading.Lock()
        self._verbose_history = []
        self._total = 0
        self._completed = 0
        self._started_at = None

    def start(self, message, total=None):
        self._message = message
        if total is not None:
            self._total = total
            self._completed = 0
            self._started_at = time.monotonic()
        self._running = True
        if self._interactive:
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
            self._start_input_listener()
        else:
            print(self._render())

    def update(self, message, completed=None):
        self._message = message
        if completed is not None:
            self._completed = min(completed, self._total)
        if not self._interactive and self._running:
            print(self._render())

    def stop(self, message=None):
        self._running = False
        self._input_running = False
        if self._thread:
            self._thread.join()
            self._thread = None
        if self._input_thread:
            self._input_thread.join(timeout=0.5)
            self._input_thread = None
        if self._interactive:
            with self._output_lock:
                sys.stdout.write("\r\033[K")
                if message:
                    sys.stdout.write(f"{message}\n")
                sys.stdout.flush()
        elif message:
            print(message)

    def verbose_log(self, message):
        """Print a detail only while the extended view is open."""
        with self._output_lock:
            self._verbose_history.append(message)
            if not self._verbose:
                return
            if not self._interactive:
                print(f"[verbose] {message}")
                return
            sys.stdout.write("\r\033[K")
            sys.stdout.write(f"{BLUE}[verbose]{RESET} {message}\n")
            sys.stdout.write(
                f"\r{self._frames[self._frame % len(self._frames)]} {self._render()}"
            )
            sys.stdout.flush()

    def _toggle_verbose(self):
        with self._output_lock:
            self._verbose = not self._verbose
            if self._interactive:
                self._redraw_with_history_locked()

    def _redraw_with_history_locked(self):
        """Redraw the status line and visible verbose history atomically."""
        if self._verbose:
            sys.stdout.write("\r\033[K")
            for message in self._verbose_history:
                sys.stdout.write(f"{BLUE}[verbose]{RESET} {message}\n")
            sys.stdout.write(
                f"\r{self._frames[self._frame % len(self._frames)]} {self._render()}"
            )
        else:
            history_lines = len(self._verbose_history)
            sys.stdout.write("\r\033[K")
            for _ in range(history_lines):
                sys.stdout.write("\033[1A\r\033[K")
            sys.stdout.write(
                f"\r{self._frames[self._frame % len(self._frames)]} {self._render()}"
            )
        sys.stdout.flush()

    def _start_input_listener(self):
        if self._input_thread and self._input_thread.is_alive():
            return
        self._input_running = True
        self._input_thread = threading.Thread(
            target=self._listen_for_toggle,
            daemon=True
        )
        self._input_thread.start()

    def _listen_for_toggle(self):
        try:
            import msvcrt
            while self._input_running:
                if msvcrt.kbhit() and msvcrt.getwch().lower() == "v":
                    self._toggle_verbose()
                time.sleep(0.05)
        except ImportError:
            return

    def _clear_line(self):
        if self._interactive:
            with self._output_lock:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()

    def _animate(self):
        while self._running:
            frame = self._frames[self._frame % len(self._frames)]
            with self._output_lock:
                sys.stdout.write(f"\r{frame} {self._render()}")
                sys.stdout.flush()
            self._frame += 1
            time.sleep(0.12)

    def _render(self):
        if not self._total:
            return self._message
        percentage = self._completed / self._total * 100
        eta = self._format_eta()
        verbose = f" | {BLUE}V:{'ON' if self._verbose else 'OFF'}{RESET}"
        return f"{self._message} | {percentage:5.1f}% | ETA {eta}{verbose}"

    def _format_eta(self):
        if not self._started_at or self._completed <= 0:
            return "--:--"
        elapsed = time.monotonic() - self._started_at
        remaining = elapsed / self._completed * (self._total - self._completed)
        minutes, seconds = divmod(max(0, int(remaining)), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


def _search_params(keyword, cursor=None):
    """Build Bluesky search parameters without sending a placeholder cursor."""
    params = {"q": keyword.lower(), "limit": 100}
    if cursor:
        params["cursor"] = cursor
    return models.AppBskyFeedSearchPosts.Params(**params)


def display_configuration():
    """Display a concise summary of the active settings."""
    print(
        f"\nGraphlex: {len(KEYWORDS)} keywords | "
        f"{DATE_START:%Y-%m-%d} to {DATE_END:%Y-%m-%d} | "
        f"output: {OUTPUT_DIR}"
    )


def confirm_start():
    """Prompt user to confirm or modify settings before starting."""
    global VERBOSE_ENABLED

    display_configuration()

    print(
        f"{BLUE}[1] Start  [2] Dates  [3] Locations  [4] Output  "
        f"[5] All settings  [6] Exit  [V] Verbose: "
        f"{'ON' if VERBOSE_ENABLED else 'OFF'}{RESET}"
    )

    while True:
        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == "1":
            return True
        elif choice == "2":
            modify_dates()
            display_configuration()
        elif choice == "3":
            modify_locations()
            display_configuration()
        elif choice == "4":
            modify_output_dir()
            display_configuration()
        elif choice == "5":
            modify_all_settings()
            display_configuration()
        elif choice == "6":
            print("\nAnalysis cancelled by user.")
            return False
        elif choice.lower() == "v":
            VERBOSE_ENABLED = not VERBOSE_ENABLED
            display_configuration()
        else:
            print("Invalid choice. Choose a blue button or press V.")


def modify_dates():
    """Allow user to modify date range."""
    global DATE_START, DATE_END

    print(f"\nCurrent date range: {DATE_START.strftime('%Y-%m-%d')} to "
          f"{DATE_END.strftime('%Y-%m-%d')}")

    start_date_default = DATE_START.strftime('%Y-%m-%d')
    start_input = input(
        f"Enter start date (YYYY-MM-DD) or press Enter to keep [{start_date_default}]: "
    ).strip()

    if start_input:
        try:
            DATE_START = datetime.strptime(start_input, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            print(f"Updated start date: {DATE_START.strftime('%Y-%m-%d')}")
        except ValueError:
            print("Invalid date format. Keeping current value.")

    end_date_default = DATE_END.strftime('%Y-%m-%d')
    end_input = input(
        f"Enter end date (YYYY-MM-DD) or press Enter to keep [{end_date_default}]: "
    ).strip()

    if end_input:
        try:
            DATE_END = datetime.strptime(end_input, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            print(f"Updated end date: {DATE_END.strftime('%Y-%m-%d')}")
        except ValueError:
            print("Invalid date format. Keeping current value.")

    if DATE_START >= DATE_END:
        print("WARNING: Start date is after or equal to end date!")


def modify_locations():
    """Allow user to modify location keywords."""
    global LOCATION_KEYWORDS

    print(f"\nCurrent location keywords: {', '.join(LOCATION_KEYWORDS)}")
    user_input = input(
        "Enter location keywords (comma-separated) or press Enter to keep current: "
    ).strip()

    if user_input:
        keywords_list = [keyword.strip() for keyword in user_input.split(",")
                         if keyword.strip()]
        LOCATION_KEYWORDS = keywords_list
        if LOCATION_KEYWORDS:
            print(f"Updated location keywords: {', '.join(LOCATION_KEYWORDS)}")
        else:
            LOCATION_KEYWORDS = DEFAULT_LOCATION_KEYWORDS.copy()
            print("No valid keywords provided. Keeping current value.")


def modify_output_dir():
    """Allow user to modify output directory."""
    global OUTPUT_DIR

    print(f"\nCurrent output directory: {OUTPUT_DIR}")
    user_input = input(
        "Enter output directory path or press Enter to keep current: "
    ).strip()

    if user_input:
        OUTPUT_DIR = user_input
        print(f"Updated output directory: {OUTPUT_DIR}")


def modify_all_settings():
    """Modify all configurable settings in sequence."""
    print("\n" + "="*80)
    print("MODIFY ALL SETTINGS")
    print("="*80)
    modify_dates()
    modify_locations()
    modify_output_dir()
    print("\nAll settings updated!")


def _run_collection_and_analysis():
    """Internal helper: collect posts and run analyses (original top-level flow).
    Returns True on success.
    """
    # --- CONFIGURATION REVIEW AND CONFIRMATION ---
    if not confirm_start():
        return False

    # --- INITIALIZE ARCHIVE ---
    archive = None
    if ARCHIVE_ENABLED:
        archive = RunArchive(ARCHIVE_DIR)
        archive.initialize_run()
        archive.update_configuration({
            "date_range": {
                "start": DATE_START.strftime('%Y-%m-%d'),
                "end": DATE_END.strftime('%Y-%m-%d')
            },
            "location_keywords": LOCATION_KEYWORDS,
            "analyses_run": [cfg["name"] for cfg in ANALYSIS_CONFIGS],
            "total_keywords": len(KEYWORDS),
            "min_co_occurrences": 1
        })

    # --- LOGIN ---
    progress = ProgressIndicator(verbose=VERBOSE_ENABLED)
    progress.start("Connecting to Bluesky")
    client = Client()
    try:
        client.login(HANDLE, PASSWORD)
    except UnauthorizedError:
        progress.stop()
        message = (
            "Authentication failed. Check BLUESKY_HANDLE and "
            "BLUESKY_PASSWORD in .env. Use a Bluesky app password."
        )
        if archive:
            archive.add_error(message)
            archive.finalize_run()
        print(f"ERROR: {message}")
        return False
    progress.stop("Connected to Bluesky")
    total_steps = len(KEYWORDS) + len(ANALYSIS_CONFIGS)
    progress.start("Collecting posts", total=total_steps)

    records = []

    for keyword_index, keyword in enumerate(KEYWORDS):
        cursor = None
        page_count = 0
        while True:
            if page_count >= 1000:
                break
            progress.update(
                f"Collecting posts with keyword '{keyword}'",
                completed=keyword_index
            )
            try:
                params = _search_params(keyword, cursor)
                feed = client.app.bsky.feed.search_posts(params)
                cursor = json.loads(feed.json()).get("cursor")
                page_count += 1
                posts = feed.posts or []
                progress.verbose_log(
                    f"{keyword}: page {page_count}, {len(posts)} posts, "
                    f"cursor received={bool(cursor)}"
                )
                for post in posts:
                    text = getattr(post.record, "text", "")
                    created_at = getattr(post.record, "created_at", "")
                    author = post.author
                    handle = getattr(author, "handle", "")
                    display_name = getattr(author, "display_name", "") or ""
                    description = getattr(author, "description", "") or ""

                    author_text = ((description or "") + (display_name or "")).lower()
                    location_match = True

                    if created_at:
                        try:
                            dt = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            ).astimezone(timezone.utc)
                        except (ValueError, AttributeError):
                            continue
                        if not DATE_START <= dt <= DATE_END:
                            continue
                    else:
                        continue

                    sentiment_score = TextBlob(text).sentiment.polarity
                    if sentiment_score > 0.1:
                        sentiment_label = "positive"
                    elif sentiment_score < -0.1:
                        sentiment_label = "negative"
                    else:
                        sentiment_label = "neutral"

                    post_type = "original"
                    final_text = text

                    if hasattr(post, "post") and hasattr(post.post, "record"):
                        record_obj = post.post.record
                        if (hasattr(record_obj, "embed") and
                            hasattr(record_obj.embed, "record") and
                                hasattr(record_obj.embed.record, "value")):
                            embed_value = record_obj.embed.record.value
                            if hasattr(embed_value, "text"):
                                post_type = "repost"
                                final_text = embed_value.text
                    elif (hasattr(post, "repost") and
                          hasattr(post.repost, "record") and
                          hasattr(post.repost.record, "text")):
                        post_type = "repost"
                        final_text = post.repost.record.text

                    if location_match:
                        records.append({
                            "keyword": keyword,
                            "type": post_type,
                            "author": display_name,
                            "handle": handle,
                            "bio": description,
                            "text": final_text,
                            "date": dt.strftime("%Y-%m-%d") if dt else "",
                            "sentiment": sentiment_label,
                            "score": sentiment_score
                        })

                time.sleep(2)

            except Exception as e:
                progress.stop()
                print(f"WARNING: Error searching for '{keyword}': {e}")
                progress.start("Collecting posts")
                continue

        progress.update(
            f"Collected keyword {keyword_index + 1}/{len(KEYWORDS)}",
            completed=keyword_index + 1
        )

    progress.stop(f"Collected {len(records)} posts")

    if records:
        if archive:
            archive.set_total_posts(len(records))

        df_all = pd.DataFrame(records)

        for config_idx, analysis_config in enumerate(ANALYSIS_CONFIGS, 1):
            config_name = analysis_config["name"]
            config_keywords = analysis_config["keywords"]
            description = analysis_config["description"]

            progress.stop()
            if archive:
                analysis_output_dir = archive.get_analysis_dir(config_name)
            else:
                analysis_output_dir = f"{OUTPUT_DIR}/{config_name}"
                os.makedirs(analysis_output_dir, exist_ok=True)

            output_file = f"{analysis_output_dir}/bluesky_posts_complex.csv"

            progress.start(
                f"Analysis {config_idx}/{len(ANALYSIS_CONFIGS)}: {config_name}"
            )

            mask = df_all['keyword'].isin(config_keywords)
            df = df_all[mask].copy()

            if len(df) > 0:
                df.to_csv(output_file, index=False)
                
                if archive:
                    archive.add_file(f"{config_name}/bluesky_posts_complex.csv")

                sentiment_counts = df["sentiment"].value_counts()
                fig = plt.figure()
                sentiment_counts.plot(
                    kind="bar",
                    title=f"Sentiment distribution - {description}"
                )
                plt.xlabel("Sentiment")
                plt.ylabel("Count")
                plt.tight_layout()
                sentiment_file = f"{analysis_output_dir}/sentiment_distribution.png"
                plt.savefig(sentiment_file, dpi=300, bbox_inches='tight')
                plt.close(fig)
                if archive:
                    archive.add_file(f"{config_name}/sentiment_distribution.png")

                progress.update(
                    f"Analysis {config_idx}: calculating co-occurrences"
                )
                new_df = {"w1": [], "w2": [], "n": []}
                for kws in list(combinations(config_keywords, 2)):
                    all_ks = None
                    for kw in kws:
                        if all_ks is None:
                            all_ks = df.text.str.contains(kw, case=False, na=False)
                        else:
                            all_ks = all_ks & df.text.str.contains(kw, case=False, na=False)
                    new_df["w1"].append(kws[0])
                    new_df["w2"].append(kws[1])
                    new_df["n"].append(all_ks.sum())

                grafo_file = f"{analysis_output_dir}/grafo.xlsx"
                pd.DataFrame(new_df).to_excel(grafo_file)
                if archive:
                    archive.add_file(f"{config_name}/grafo.xlsx")
                    archive.update_results_summary(config_name, {
                        "posts_count": len(df),
                        "keywords_count": len(config_keywords)
                    })
                progress.verbose_log(
                    f"{config_name}: wrote analysis outputs to "
                    f"{analysis_output_dir}"
                )
                progress.update(
                    f"Completed analysis {config_idx}/{len(ANALYSIS_CONFIGS)}",
                    completed=len(KEYWORDS) + config_idx
                )
            else:
                progress.stop()
                print(f"WARNING: No posts found for {description}.")
                progress.start(
                    f"Analysis {config_idx}/{len(ANALYSIS_CONFIGS)}: {config_name}"
                )
                progress.update(
                    f"Completed analysis {config_idx}/{len(ANALYSIS_CONFIGS)}",
                    completed=len(KEYWORDS) + config_idx
                )
                if archive:
                    archive.add_warning(f"No posts found for {description}")

    else:
        progress.stop()
        print("\nWARNING: No posts found with the specified criteria.")
        if archive:
            archive.add_warning("No posts found with the specified criteria")

    # --- FINALIZE ARCHIVE ---
    if archive:
        archive.finalize_run()

    progress.stop("Analysis complete")

    return True


def main(argv=None):
    """Console entry point."""
    try:
        result = _run_collection_and_analysis()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user (Ctrl+C).")
        print("No further posts or analysis will be processed.")
        return 130
    return 0 if result else 1


if __name__ == "__main__":
    main()
