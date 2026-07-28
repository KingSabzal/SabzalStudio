"""Trend tab: find what is trending, then let the AI propose titles for it.

The difference from the Create tab is that nothing here is chosen by hand.
Trends are scanned across nine sources, the model proposes ten to fifteen
titles, each is scored, and picking one starts a run whose style, length,
orientation, narrator and captions were all decided from the trend itself.
"""

from __future__ import annotations

import streamlit as st

from utility.core import settings_store
from utility.trends.trend_sources import TREND_SOURCES
from utility.ui.run_helper import run_pipeline

CATEGORIES = ["All", "Technology", "Entertainment", "Science", "Politics",
              "Sports", "Health", "Business", "Culture", "Mystery",
              "Controversy"]


def _score_colour(score: float) -> str:
    if score >= 80:
        return "🟢"
    if score >= 65:
        return "🟡"
    return "🟠"


def render():
    st.caption(
        f"Scans {len(TREND_SOURCES)} sources for what is trending right now, "
        f"then asks the model for titles built on them. Everything about the "
        f"video is decided automatically."
    )

    missing = settings_store.missing_settings()
    if missing:
        st.error("Fill these in on the Settings tab first: " + ", ".join(missing))
        return

    left, middle, right = st.columns([2, 1, 1])
    category = left.selectbox("Focus", CATEGORIES)
    count = middle.slider("How many titles", 10, 15, 12)
    refresh = right.checkbox("Ignore the cache", value=False,
                             help="Trends are cached for an hour. Tick this "
                                  "to scan again now.")

    if st.button("Find trends and suggest titles", type="primary"):
        status = st.status("Scanning trend sources...", expanded=True)

        def progress(source, message):
            status.write(f"{source}: {message}")

        try:
            from utility.trends.viral_title_generator import ViralTitleGenerator
            generator = ViralTitleGenerator()
            result = generator.generate(count=count, force_refresh=refresh,
                                        category=category, progress=progress)
            status.update(label="Done", state="complete", expanded=False)
            st.session_state["trend_result"] = result
        except Exception as error:
            status.update(label="Failed", state="error")
            st.error(f"{type(error).__name__}: {error}")
            return

    result = st.session_state.get("trend_result")
    if not result:
        return

    suggestions = result.get("suggestions", [])
    if not suggestions:
        st.warning("No suggestion scored well enough. Try scanning again.")
        return

    top = st.columns(3)
    top[0].metric("Titles", len(suggestions))
    top[1].metric("Average uniqueness", f"{result.get('uniqueness_average', 0)}%")
    top[2].metric("Trends", result.get("last_updated", "just now"))

    st.markdown("#### Pick one and it starts")

    for index, item in enumerate(suggestions):
        settings = item["settings"]
        with st.container(border=True):
            head, action = st.columns([5, 1])
            head.markdown(
                f"{_score_colour(item['viral_score'])} **{item['title']}**"
            )
            head.caption(
                f"score {item['viral_score']}  ·  {item['badge'].get('label', '')}"
                f"  ·  {item['category']}  ·  from: {item['source_trend'][:60]}"
            )
            head.caption(
                f"{settings['video_style']}  ·  {settings['duration_seconds']}s  "
                f"·  {settings['orientation']}  ·  {settings['voice']}  ·  "
                f"captions: {settings['caption_style']}"
            )
            if item.get("angle"):
                head.caption(f"Angle: {item['angle']}")

            if action.button("Make it", key=f"trend_go_{index}", type="primary"):
                overrides = {
                    "VIDEO_STYLE": settings["video_style"],
                    "VIDEO_DURATION": str(settings["duration_seconds"]),
                    "VIDEO_ORIENTATION": settings["orientation"],
                    "EDGETTS_VOICE": settings["voice"],
                    "CAPTION_STYLE": settings["caption_style"],
                    "CAPTIONS_ENABLED": "true",
                    "CAPTION_EMOJI": "on" if settings.get("emoji_enabled") else "off",
                    "SFX_ENABLED": "true",
                    "SFX_DENSITY": settings.get("sfx_density", "medium"),
                }
                run_pipeline(item["topic"], overrides)

            with st.expander("Why this scored what it did"):
                for name, value in item["score_components"].items():
                    st.progress(min(value / 100, 1.0),
                                text=f"{name.replace('_', ' ')}: {value:.0f}")
                if item.get("keywords"):
                    st.caption("Keywords: " + ", ".join(item["keywords"]))
