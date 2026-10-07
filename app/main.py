"""
Main module for collecting and analyzing Bluesky posts (packaged)
Provides `main()` entry point for console script.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from itertools import combinations

import matplotlib.pyplot as plt
import pandas as pd
from atproto import Client, models
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


def _search_params(keyword, cursor=None):
    """Build Bluesky search parameters without sending a placeholder cursor."""
    params = {"q": keyword.lower(), "limit": 100}
    if cursor:
        params["cursor"] = cursor
    return models.AppBskyFeedSearchPosts.Params(**params)


def display_configuration():
    """Display current configuration settings to the user."""
    print("\n" + "="*80)
    print("CONFIGURATION REVIEW")
    print("="*80)

    print("\nANALYSIS CONFIGURATIONS:")
    for idx, config in enumerate(ANALYSIS_CONFIGS, 1):
        print(f"   {idx}. {config['name']}: {config['description']}")
        print(f"      Keywords: {len(config['keywords'])}")

    print(f"\nTOTAL UNIQUE KEYWORDS: {len(KEYWORDS)}")
    print(f"   - Main keywords: {len(MAIN_KEYWORDS)}")
    print(f"   - Group 4 keywords: {len(GROUP_KEYWORDS)}")
    print(f"   - Extra keywords: {len(EXTRA_KEYWORDS)}")

    print(f"\nDATE RANGE:")
    print(f"   Start: {DATE_START.strftime('%Y-%m-%d')}")
    print(f"   End: {DATE_END.strftime('%Y-%m-%d')}")

    print(f"\nLOCATION FILTERS:")
    print(f"   {', '.join(LOCATION_KEYWORDS)}")

    print(f"\nOUTPUT DIRECTORY:")
    print(f"   {OUTPUT_DIR}")

    print(f"\nCREDENTIALS:")
    if HANDLE and PASSWORD:
        print(f"   Handle: {HANDLE}")
        print("   Password: ****** (configured)")
    else:
        print("   WARNING: Credentials not found in environment variables!")

    print("\n" + "="*80)


def confirm_start():
    """Prompt user to confirm or modify settings before starting."""
    display_configuration()

    print("\nOptions:")
    print("  1. Start analysis with current settings")
    print("  2. Modify date range")
    print("  3. Modify location keywords")
    print("  4. Modify output directory")
    print("  5. Modify all settings")
    print("  6. Exit")

    while True:
        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == "1":
            print("\nStarting analysis...")
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
        else:
            print("Invalid choice. Please enter 1-6.")


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
    print("\nConnecting to Bluesky...")
    client = Client()
    client.login(HANDLE, PASSWORD)
    print("Login successful!")

    print("\n" + "="*80)
    print("COLLECTING DATA FOR ALL KEYWORDS (ONCE)")
    print(f"Total keywords: {len(KEYWORDS)}")
    print("="*80)

    records = []

    for keyword in KEYWORDS:
        cursor = None
        page_count = 0
        while True:
            if page_count >= 1000:
                break
            print(f"\nSearching posts with keyword: {keyword}")
            try:
                params = _search_params(keyword, cursor)
                feed = client.app.bsky.feed.search_posts(params)
                cursor = json.loads(feed.json()).get("cursor")
                page_count += 1
                posts = feed.posts or []
                print(f"   Found {len(posts)} results | reached cursor {cursor}")

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
                print(f"WARNING: Error searching for '{keyword}': {e}")
                continue

    print("\n" + "="*80)
    print(f"DATA COLLECTION COMPLETE: {len(records)} total posts collected")
    print("Now filtering and saving for each analysis...")
    print("="*80)

    if records:
        if archive:
            archive.set_total_posts(len(records))

        df_all = pd.DataFrame(records)

        for config_idx, analysis_config in enumerate(ANALYSIS_CONFIGS, 1):
            config_name = analysis_config["name"]
            config_keywords = analysis_config["keywords"]
            description = analysis_config["description"]

            if archive:
                analysis_output_dir = archive.get_analysis_dir(config_name)
            else:
                analysis_output_dir = f"{OUTPUT_DIR}/{config_name}"
                os.makedirs(analysis_output_dir, exist_ok=True)

            output_file = f"{analysis_output_dir}/bluesky_posts_complex.csv"

            print("\n" + "="*80)
            print(f"ANALYSIS {config_idx}/3: {description}")
            print(f"Keywords: {len(config_keywords)}")
            print(f"Output directory: {analysis_output_dir}")
            print("="*80)

            mask = df_all['keyword'].isin(config_keywords)
            df = df_all[mask].copy()

            filtered_count = len(df)
            total_count = len(df_all)
            print(f"Filtered {filtered_count} posts (from {total_count} total)")

            if len(df) > 0:
                df.to_csv(output_file, index=False)
                print(f"Saved {len(df)} posts in '{output_file}'")
                
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
                print(f"Saved sentiment chart in '{sentiment_file}'")
                
                if archive:
                    archive.add_file(f"{config_name}/sentiment_distribution.png")

                print(f"\nCalculating co-occurrences for {len(config_keywords)} keywords...")
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
                print(f"Saved co-occurrence matrix in '{grafo_file}'")
                
                if archive:
                    archive.add_file(f"{config_name}/grafo.xlsx")
                    archive.update_results_summary(config_name, {
                        "posts_count": len(df),
                        "keywords_count": len(config_keywords)
                    })
            else:
                print(f"WARNING: No posts found for {description}.")
                if archive:
                    archive.add_warning(f"No posts found for {description}")

    else:
        print("\nWARNING: No posts found with the specified criteria.")
        if archive:
            archive.add_warning("No posts found with the specified criteria")

    # --- FINALIZE ARCHIVE ---
    if archive:
        archive.finalize_run()

    print("\n" + "="*80)
    print("ALL ANALYSES COMPLETE!")
    print("="*80)

    return True


def main(argv=None):
    """Console entry point."""
    _run_collection_and_analysis()


if __name__ == "__main__":
    main()
