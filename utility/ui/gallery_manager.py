"""Keeps a record of every finished video so the gallery can list them.

Each render writes its file into outputs/ under the title it will be uploaded
with, and appends a row to outputs/gallery.json. Keeping the index separate
from the folder listing means the gallery can show the title, the style, the
duration and the upload packages, not just a filename.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List

_LOCK = threading.Lock()

INDEX_NAME = "gallery.json"


def project_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", ".."))


def outputs_dir() -> str:
    path = os.path.join(project_root(), "outputs")
    os.makedirs(path, exist_ok=True)
    return path


def index_path() -> str:
    return os.path.join(outputs_dir(), INDEX_NAME)


def load() -> List[Dict[str, Any]]:
    """Every recorded video, newest first."""
    path = index_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            entries = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(entries, list):
        return []
    # Drop rows whose file has since been deleted from disk.
    alive = [e for e in entries if os.path.exists(
        os.path.join(outputs_dir(), e.get("filename", "")))]
    return sorted(alive, key=lambda e: e.get("created", ""), reverse=True)


def record(filename: str, topic: str = "", title: str = "", style: str = "",
           duration: float = 0.0, orientation: str = "",
           packages_file: str = "", voice: str = "") -> Dict[str, Any]:
    """Add one finished video to the index."""
    entry = {
        "filename": os.path.basename(filename),
        "topic": topic,
        "title": title,
        "style": style,
        "duration": round(float(duration or 0), 1),
        "orientation": orientation,
        "packages_file": os.path.basename(packages_file) if packages_file else "",
        "voice": voice,
        "created": datetime.now().isoformat(timespec="seconds"),
        "size_mb": round(os.path.getsize(
            os.path.join(outputs_dir(), os.path.basename(filename))) / (1024 * 1024), 1)
        if os.path.exists(os.path.join(outputs_dir(), os.path.basename(filename)))
        else 0.0,
    }
    with _LOCK:
        entries = []
        if os.path.exists(index_path()):
            try:
                with open(index_path(), "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, list):
                    entries = loaded
            except (OSError, json.JSONDecodeError):
                entries = []
        entries = [e for e in entries if e.get("filename") != entry["filename"]]
        entries.append(entry)
        temporary = index_path() + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, indent=2, ensure_ascii=False)
        os.replace(temporary, index_path())
    return entry


def delete(filename: str) -> bool:
    """Remove a video and its row, and its packages file if it has one."""
    name = os.path.basename(filename)
    entries = []
    removed = False
    with _LOCK:
        if os.path.exists(index_path()):
            try:
                with open(index_path(), "r", encoding="utf-8") as handle:
                    entries = json.load(handle)
            except (OSError, json.JSONDecodeError):
                entries = []
        keep = []
        for entry in entries:
            if entry.get("filename") == name:
                removed = True
                for target in (entry.get("filename"), entry.get("packages_file")):
                    if not target:
                        continue
                    try:
                        os.remove(os.path.join(outputs_dir(), target))
                    except OSError:
                        pass
            else:
                keep.append(entry)
        temporary = index_path() + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(keep, handle, indent=2, ensure_ascii=False)
        os.replace(temporary, index_path())
    return removed


def stats() -> Dict[str, Any]:
    """Totals for the gallery header."""
    entries = load()
    return {
        "count": len(entries),
        "total_minutes": round(sum(e.get("duration", 0) for e in entries) / 60, 1),
        "total_mb": round(sum(e.get("size_mb", 0) for e in entries), 1),
    }
