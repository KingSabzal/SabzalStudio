"""Gallery tab: every video this project has made.

Each row shows the video itself, what it was made from, and the upload
packages that went with it, so a finished video can be reviewed and published
without leaving the interface.
"""

from __future__ import annotations

import os

import streamlit as st

from utility.ui import gallery_manager


def render():
    entries = gallery_manager.load()
    totals = gallery_manager.stats()

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Videos", totals["count"])
    col_b.metric("Total length", f"{totals['total_minutes']} min")
    col_c.metric("On disk", f"{totals['total_mb']} MB")

    if not entries:
        st.info(
            "Nothing here yet. Make a video on the Create tab and it will "
            "appear in this list."
        )
        return

    folder = gallery_manager.outputs_dir()

    search = st.text_input("Filter", placeholder="search by title or topic")
    if search:
        needle = search.lower()
        entries = [e for e in entries
                   if needle in e.get("title", "").lower()
                   or needle in e.get("topic", "").lower()
                   or needle in e.get("style", "").lower()]
        if not entries:
            st.warning("Nothing matches that.")
            return

    for entry in entries:
        path = os.path.join(folder, entry["filename"])
        title = entry.get("title") or entry.get("topic") or entry["filename"]

        with st.container(border=True):
            video_col, detail_col = st.columns([1, 2])

            with video_col:
                if os.path.exists(path):
                    st.video(path)

            with detail_col:
                st.markdown(f"**{title}**")
                facts = [
                    entry.get("style", ""),
                    f"{entry.get('duration', 0)}s",
                    entry.get("orientation", ""),
                    f"{entry.get('size_mb', 0)} MB",
                    entry.get("created", "")[:16].replace("T", " "),
                ]
                st.caption("  ·  ".join(f for f in facts if f))
                if entry.get("voice"):
                    st.caption(f"Narrated by {entry['voice']}")
                st.code(entry["filename"], language=None)

                buttons = st.columns(3)
                if os.path.exists(path):
                    with open(path, "rb") as handle:
                        buttons[0].download_button(
                            "Video", handle, file_name=entry["filename"],
                            key=f"dl_{entry['filename']}",
                        )

                packages_path = os.path.join(folder, entry.get("packages_file", ""))
                if entry.get("packages_file") and os.path.exists(packages_path):
                    with open(packages_path, "r", encoding="utf-8") as handle:
                        content = handle.read()
                    buttons[1].download_button(
                        "Packages", content, file_name=entry["packages_file"],
                        key=f"pk_{entry['filename']}",
                    )
                    with st.expander("Upload packages"):
                        st.text(content)

                if buttons[2].button("Delete", key=f"rm_{entry['filename']}"):
                    gallery_manager.delete(entry["filename"])
                    st.rerun()
