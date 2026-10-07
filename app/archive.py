"""
Archive management module for keyword network analysis runs (packaged)
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any


class RunArchive:
    """Manages archiving of analysis runs with UUID-based directories"""

    def __init__(self, base_archive_dir: str = "exports/runs"):
        self.base_archive_dir = Path(base_archive_dir)
        self.run_uuid = None
        self.run_id = None
        self.run_dir = None
        self.manifest = None
        self.start_time = None
        self.errors = []
        self.warnings = []

    def initialize_run(self) -> str:
        self.run_uuid = str(uuid.uuid4())
        short_uuid = self.run_uuid.split('-')[0]
        timestamp = datetime.now(timezone.utc)
        self.start_time = timestamp
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        self.run_id = f"{timestamp_str}_{short_uuid}"
        self.run_dir = self.base_archive_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.manifest = {
            "run_id": self.run_id,
            "uuid": self.run_uuid,
            "timestamp_start": timestamp.isoformat(),
            "timestamp_end": None,
            "duration_seconds": None,
            "configuration": {},
            "results_summary": {
                "total_posts_collected": 0,
                "analyses": {}
            },
            "files_generated": [],
            "errors": [],
            "warnings": []
        }
        self._save_manifest()
        print(f"Archive: {self.run_id}")
        return str(self.run_dir)

    def get_analysis_dir(self, analysis_name: str) -> str:
        if not self.run_dir:
            raise RuntimeError("Run not initialized. Call initialize_run() first.")
        analysis_dir = self.run_dir / analysis_name
        analysis_dir.mkdir(parents=True, exist_ok=True)
        return str(analysis_dir)

    def update_configuration(self, config: Dict[str, Any]):
        self.manifest["configuration"].update(config)
        self._save_manifest()

    def update_results_summary(self, analysis_name: str, summary: Dict[str, Any]):
        self.manifest["results_summary"][analysis_name] = summary
        self._save_manifest()

    def set_total_posts(self, count: int):
        self.manifest["results_summary"]["total_posts_collected"] = count
        self._save_manifest()

    def add_file(self, file_path: str):
        if file_path not in self.manifest["files_generated"]:
            self.manifest["files_generated"].append(file_path)
            self._save_manifest()

    def add_error(self, error: str):
        self.errors.append(error)
        self.manifest["errors"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": error
        })
        self._save_manifest()

    def add_warning(self, warning: str):
        self.warnings.append(warning)
        self.manifest["warnings"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": warning
        })
        self._save_manifest()

    def finalize_run(self):
        if not self.start_time:
            raise RuntimeError("Run not initialized")
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds()
        self.manifest["timestamp_end"] = end_time.isoformat()
        self.manifest["duration_seconds"] = round(duration, 2)
        self._save_manifest()
        self._update_index()
        print(
            f"Archive finalized: {self.run_id} | "
            f"{duration:.2f}s | {len(self.manifest['files_generated'])} files"
        )

    def _save_manifest(self):
        if not self.run_dir:
            return
        manifest_path = self.run_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)

    def _update_index(self):
        index_path = self.base_archive_dir / "index.json"
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"runs": []}
        run_entry = {
            "run_id": self.run_id,
            "uuid": self.run_uuid,
            "timestamp": self.manifest["timestamp_start"],
            "duration_seconds": self.manifest["duration_seconds"],
            "total_posts": self.manifest["results_summary"]["total_posts_collected"],
            "analyses": list(self.manifest["results_summary"]["analyses"].keys()),
            "files_count": len(self.manifest["files_generated"]),
            "has_errors": len(self.errors) > 0,
            "has_warnings": len(self.warnings) > 0
        }
        index["runs"].insert(0, run_entry)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)


# Utility functions

def list_runs(base_archive_dir: str = "exports/runs") -> List[Dict[str, Any]]:
    index_path = Path(base_archive_dir) / "index.json"
    if not index_path.exists():
        return []
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    return index.get("runs", [])


def get_run_manifest(run_id: str, base_archive_dir: str = "exports/runs") -> Optional[Dict[str, Any]]:
    base_path = Path(base_archive_dir)
    manifest_path = base_path / run_id / "manifest.json"
    if not manifest_path.exists():
        for run_dir in base_path.iterdir():
            if run_dir.is_dir():
                manifest_path = run_dir / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                        if manifest.get("uuid") == run_id or manifest.get("run_id") == run_id:
                            return manifest
        return None
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_latest_run(base_archive_dir: str = "exports/runs") -> Optional[Dict[str, Any]]:
    runs = list_runs(base_archive_dir)
    return runs[0] if runs else None


def print_runs_table(limit: int = 10, base_archive_dir: str = "exports/runs"):
    runs = list_runs(base_archive_dir)
    if not runs:
        print("No archived runs found.")
        return
    print(f"\n{'='*120}")
    print(f"ARCHIVED RUNS (showing {min(limit, len(runs))} of {len(runs)})")
    print(f"{'='*120}")
    print(f"{'Run ID':<30} {'Date':<20} {'Posts':<8} {'Analyses':<12} {'Duration':<12} {'Status':<10}")
    print(f"{'-'*120}")
    for run in runs[:limit]:
        run_id = run["run_id"][:28] + ".." if len(run["run_id"]) > 30 else run["run_id"]
        timestamp = datetime.fromisoformat(run["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        posts = run["total_posts"]
        analyses = len(run["analyses"])
        duration = f"{run['duration_seconds']:.1f}s"
        status = "✓"
        if run["has_errors"]:
            status = "✗ Error"
        elif run["has_warnings"]:
            status = "⚠ Warning"
        print(f"{run_id:<30} {timestamp:<20} {posts:<8} {analyses:<12} {duration:<12} {status:<10}")
    print(f"{'='*120}\n")


def cleanup_old_runs(keep_last_n: int = 10, base_archive_dir: str = "exports/runs"):
    import shutil
    runs = list_runs(base_archive_dir)
    if len(runs) <= keep_last_n:
        print(f"No cleanup needed. {len(runs)} runs exist, keeping last {keep_last_n}.")
        return
    runs_to_delete = runs[keep_last_n:]
    base_path = Path(base_archive_dir)
    print(f"\nCleaning up {len(runs_to_delete)} old runs...")
    for r in runs_to_delete:
        dir_to_remove = base_path / r['run_id']
        if dir_to_remove.exists():
            shutil.rmtree(dir_to_remove)
    print("Cleanup complete.")
