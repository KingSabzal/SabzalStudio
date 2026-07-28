"""Create tab: the topic, and every choice that applies to this one video.

Settings that belong to the machine (keys, the handle, the provider) live on
the Settings tab and are saved permanently. Everything on this tab describes
one particular video, so it is chosen here each time and passed to the run as
environment overrides rather than written to config.json. That way trying a
landscape version of yesterday's video does not silently change the default
for every video after it.
"""

from __future__ import annotations

import os
import streamlit as st

from utility.captions.caption_styles import CAPTION_STYLES, list_styles
from utility.core import settings_store
from utility.pipeline_manager import list_checkpoints
from utility.script.video_styles import VIDEO_STYLES, get_style as get_script_style
from utility.tts.voices import list_voices, describe
from utility.ui import gallery_manager
from utility.ui.run_helper import STAGE_LABELS, run_pipeline

PROJECT_ROOT = gallery_manager.project_root()


def render():
    saved = settings_store.read()

    missing = settings_store.missing_settings()
    if missing:
        st.error(
            "Before anything can be generated, fill these in on the Settings "
            "tab: " + ", ".join(missing)
        )

    topic = st.text_input(
        "What is the video about?",
        placeholder="deep sea creatures that glow in total darkness",
        help="A sentence works better than a single word.",
    )

    st.markdown("#### Choices for this video")
    st.caption(
        "These apply to this run only. They do not change your saved defaults."
    )

    left, middle, right = st.columns(3)

    with left:
        styles = sorted(VIDEO_STYLES)
        default_style = saved.get("VIDEO_STYLE", "facts")
        style = st.selectbox(
            "Script style", styles,
            index=styles.index(default_style) if default_style in styles else 0,
        )
        st.caption(get_script_style(style)["description"])

        duration = st.slider(
            "Length in seconds", min_value=15, max_value=600,
            value=int(saved.get("VIDEO_DURATION", "50") or 50), step=5,
            help="Roughly 140 spoken words a minute. Under 120 seconds the "
                 "script is written to Shorts rules.",
        )
        st.caption(f"About {int(duration / 60 * 140)} words of narration.")

    with middle:
        orientation = st.radio(
            "Shape", ["portrait", "landscape"],
            index=0 if saved.get("VIDEO_ORIENTATION", "portrait") == "portrait" else 1,
            horizontal=True,
            help="Portrait is 9:16 for Shorts, Reels and TikTok. "
                 "Landscape is 16:9.",
        )
        st.caption("1080x1920" if orientation == "portrait" else "1920x1080")

        voices = ["auto"] + list_voices()
        current_voice = saved.get("EDGETTS_VOICE", "auto")
        voice = st.selectbox(
            "Narrator", voices,
            index=voices.index(current_voice) if current_voice in voices else 0,
            help="'auto' picks a voice that suits the style, and keeps the "
                 "same one for the same topic.",
        )
        if voice != "auto":
            st.caption(describe(voice))
        else:
            st.caption("Chosen from the script style.")

    with right:
        caption_choices = ["auto"] + list_styles()
        current_caption = saved.get("CAPTION_STYLE", "auto")
        caption_style = st.selectbox(
            "Caption style", caption_choices,
            index=caption_choices.index(current_caption)
            if current_caption in caption_choices else 0,
        )
        if caption_style == "auto":
            st.caption("Chosen from the script style.")
        else:
            st.caption(CAPTION_STYLES[caption_style]["description"][:110] + "...")

        captions_on = st.checkbox(
            "Burn in captions",
            value=str(saved.get("CAPTIONS_ENABLED", "true")).lower() == "true",
        )
        emoji_on = st.checkbox(
            "Emoji beside key words",
            value=str(saved.get("CAPTION_EMOJI", "off")).lower() in ("on", "true"),
        )

    with st.expander("Sound and watermark for this video"):
        col_a, col_b, col_c = st.columns(3)
        sfx_on = col_a.checkbox(
            "Ambient sound effects",
            value=str(saved.get("SFX_ENABLED", "true")).lower() == "true",
        )
        sfx_density = col_a.select_slider(
            "Effect density", ["low", "medium", "high"],
            value=saved.get("SFX_DENSITY", "medium"), disabled=not sfx_on,
        )
        watermark_on = col_b.checkbox(
            "Moving handle watermark",
            value=str(saved.get("WATERMARK", "off")).lower() in ("on", "true"),
        )
        handle = col_b.text_input(
            "Handle", value=saved.get("WATERMARK_HANDLE", ""),
            disabled=not watermark_on, placeholder="@YourName",
        )
        emoji_rate = col_c.number_input(
            "Emoji per minute", min_value=1, max_value=30,
            value=int(saved.get("CAPTION_EMOJI_PER_MINUTE", "10") or 10),
            disabled=not emoji_on,
        )
        renderer = col_c.selectbox(
            "Renderer", ["moviepy", "remotion"],
            index=0 if saved.get("RENDER_ENGINE", "moviepy") == "moviepy" else 1,
        )

    # Each topic keeps its own checkpoint, so several unfinished runs can sit
    # side by side and starting a new topic never discards an old one.
    saved_runs = list_checkpoints()
    if saved_runs:
        st.markdown("#### Unfinished runs")
        st.caption(
            "Each is resumed by generating the same topic again. They do not "
            "interfere with each other."
        )
        for path, state in saved_runs:
            stage = state.get("current_stage", "")
            saved_topic = state.get("topic", "")
            row, action = st.columns([5, 1])
            row.markdown(
                f"**{STAGE_LABELS.get(stage, stage)}** — *{saved_topic}*"
            )
            if action.button("Discard", key=f"discard_{os.path.basename(path)}"):
                try:
                    os.remove(path)
                except OSError as error:
                    st.warning(f"Could not remove it: {error}")
                st.rerun()

    if st.button("Generate", type="primary",
                 disabled=bool(missing) or not topic.strip()):
        overrides = {
            "VIDEO_STYLE": style,
            "VIDEO_DURATION": str(duration),
            "VIDEO_ORIENTATION": orientation,
            "EDGETTS_VOICE": voice,
            "CAPTION_STYLE": caption_style,
            "CAPTIONS_ENABLED": "true" if captions_on else "false",
            "CAPTION_EMOJI": "on" if emoji_on else "off",
            "CAPTION_EMOJI_PER_MINUTE": str(emoji_rate),
            "SFX_ENABLED": "true" if sfx_on else "false",
            "SFX_DENSITY": sfx_density,
            "WATERMARK": "on" if watermark_on else "off",
            "WATERMARK_HANDLE": handle,
            "RENDER_ENGINE": renderer,
        }
        run_pipeline(topic.strip(), overrides)
