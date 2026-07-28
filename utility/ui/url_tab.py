"""URL tab: turn any article into a video.

Paste a news story, a Wikipedia page or any other page with real text in it.
The page is fetched, the article body is separated from the navigation and
advertising around it, the substance is measured, and every production setting
is derived from what the article turns out to be. Nothing is chosen by hand.
"""

from __future__ import annotations

import streamlit as st

from utility.core import settings_store
from utility.ui.run_helper import run_pipeline


def render():
    st.caption(
        "Paste a link to a news article, a Wikipedia page or any page with "
        "real text. Everything about the video is worked out from the article."
    )

    missing = settings_store.missing_settings()
    if missing:
        st.error("Fill these in on the Settings tab first: " + ", ".join(missing))
        return

    url = st.text_input(
        "Article address",
        placeholder="https://en.wikipedia.org/wiki/Bioluminescence",
    )

    if st.button("Read the article", disabled=not url.strip()):
        with st.status("Fetching and reading...", expanded=True) as status:
            try:
                from utility.articles.article_extractor import (
                    extract, suggest_settings,
                )
                status.write("Downloading the page...")
                article = extract(url.strip())
                status.write(
                    f"Found {article.word_count} words in "
                    f"'{article.title[:60]}'."
                )
                status.write("Working out the settings...")
                settings = suggest_settings(article)
                status.update(label="Read", state="complete", expanded=False)
                st.session_state["url_article"] = article.as_dict()
                st.session_state["url_settings"] = settings
            except Exception as error:
                status.update(label="Could not read that page", state="error")
                st.error(f"{type(error).__name__}: {error}")
                st.caption(
                    "Some sites block automated readers entirely. A Wikipedia "
                    "page or a plain news article usually works."
                )
                return

    settings = st.session_state.get("url_settings")
    article = st.session_state.get("url_article")
    if not settings:
        return

    st.markdown(f"#### {settings['topic']}")
    st.caption(
        f"From {settings['source_site']}  ·  {settings['category']}  ·  "
        f"reads as {settings['emotion']}"
    )

    quality = st.columns(3)
    quality[0].metric("Substance", f"{settings['substance_score']}/100",
                      help="How much of the page is real content rather than "
                           "navigation and advertising.")
    quality[1].metric("Words", article.get("word_count", 0) if article else 0)
    quality[2].metric("Suggested length", f"{settings['duration_seconds']}s")

    if settings["substance_score"] < 30:
        st.warning(
            "There is not much real text on that page. The script will be "
            "thin. A fuller article gives a much better video."
        )

    if settings.get("summary"):
        st.info(settings["summary"])

    with st.expander("What was found in the article"):
        if settings.get("key_facts"):
            st.markdown("**Key facts**")
            for fact in settings["key_facts"]:
                st.markdown(f"- {fact}")
        if settings.get("numbers"):
            st.markdown("**Numbers**  " + ", ".join(str(n) for n in settings["numbers"]))
        if settings.get("entities"):
            st.markdown("**Names**  " + ", ".join(settings["entities"]))
        if settings.get("quotes"):
            st.markdown("**Quotes**")
            for quote in settings["quotes"]:
                st.markdown(f"> {quote}")

    st.markdown("#### Settings chosen from the article")
    chosen = st.columns(4)
    chosen[0].markdown(f"**Style**\n\n{settings['video_style']}")
    chosen[1].markdown(f"**Shape**\n\n{settings['orientation']}")
    chosen[2].markdown(f"**Narrator**\n\n{settings['voice']}")
    chosen[3].markdown(f"**Captions**\n\n{settings['caption_style']}")
    st.caption(
        f"Music: {', '.join(settings['music_mood'])}  ·  "
        f"effects: {settings['sfx_density']}  ·  "
        f"{settings['voice_description']}"
    )

    if st.button("Make the video", type="primary"):
        overrides = {
            "VIDEO_STYLE": settings["video_style"],
            "VIDEO_DURATION": str(settings["duration_seconds"]),
            "VIDEO_ORIENTATION": settings["orientation"],
            "EDGETTS_VOICE": settings["voice"],
            "CAPTION_STYLE": settings["caption_style"],
            "CAPTIONS_ENABLED": "true",
            "SFX_ENABLED": "true",
            "SFX_DENSITY": settings["sfx_density"],
        }
        run_pipeline(settings["topic"], overrides)
