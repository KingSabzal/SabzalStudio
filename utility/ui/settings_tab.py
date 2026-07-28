"""Settings tab: keys, the provider, and the defaults for new videos.

Everything here is saved to config.json and persists. Choices that describe a
single video live on the Create tab instead.
"""

from __future__ import annotations

import os

import streamlit as st

from utility.core import settings_store
from utility.llm.llm_providers import PROVIDERS

PROVIDER_FIELDS = {
    "9router": ["ROUTER9_URL", "ROUTER9_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "nvidia": ["NVIDIA_NIM_KEY", "NVIDIA_NIM_URL"],
    "cloudflare": ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"],
}


def _test_provider(provider: str) -> tuple:
    """Ask the provider what models it has. Proves the credentials work."""
    try:
        from utility.llm.llm_router import SmartLLMRouter
        models = SmartLLMRouter().available_models(refresh=True)
        if not models:
            return False, "Connected, but no text models were offered."
        return True, f"Connected. {len(models)} models available, " \
                     f"starting with {models[0]}."
    except Exception as error:
        return False, f"{type(error).__name__}: {str(error)[:160]}"


def render():
    values = settings_store.read()
    updated = {}

    st.caption("Saved to config.json. There is no .env file.")

    # ---------------------------------------------------------------
    st.markdown("#### AI provider")
    st.caption(
        "Pick one. No model is configured: the provider is asked what it has "
        "and the run works down that list, so a busy model never stops a video."
    )
    ids = list(PROVIDERS)
    current = values.get("LLM_PROVIDER", "openrouter")
    provider = st.selectbox(
        "Provider", ids,
        index=ids.index(current) if current in ids else 0,
        format_func=lambda pid: PROVIDERS[pid]["name"],
    )
    updated["LLM_PROVIDER"] = provider
    st.caption(PROVIDERS[provider]["description"])
    if PROVIDERS[provider].get("signup"):
        st.caption(f"Get credentials: {PROVIDERS[provider]['signup']}")

    for key in PROVIDER_FIELDS[provider]:
        spec = settings_store.SCHEMA[key]
        updated[key] = st.text_input(
            spec["label"], value=values.get(key, ""),
            type="password" if spec.get("secret") else "default",
            key=f"set_{key}",
        )
    if PROVIDERS[provider].get("notes"):
        st.info(PROVIDERS[provider]["notes"])

    updated["LLM_MODEL"] = st.text_input(
        "Pin one model (optional)", value=values.get("LLM_MODEL", ""),
        help="Leave blank so the router can fall back between models.",
    )

    if st.button("Test the connection"):
        for key, value in updated.items():
            if value:
                os.environ[key] = str(value)
        ok, message = _test_provider(provider)
        (st.success if ok else st.error)(message)

    st.divider()

    # ---------------------------------------------------------------
    st.markdown("#### Media keys")
    col_a, col_b = st.columns(2)
    updated["PEXELS_API_KEY"] = col_a.text_input(
        "Pexels key (required)", value=values.get("PEXELS_API_KEY", ""),
        type="password",
        help="Free from pexels.com/api/new. The first and usually best source.",
    )
    updated["PIXABAY_API_KEY"] = col_b.text_input(
        "Pixabay key (optional but recommended)",
        value=values.get("PIXABAY_API_KEY", ""), type="password",
        help="Free from pixabay.com/api/key. Adds a second large library of "
             "video, photos, music and sound effects, which makes a missing "
             "clip much less likely.",
    )
    st.caption(
        "Every other source needs no key: Mixkit, Coverr, Openverse, "
        "Wikimedia, NASA, the Met, Library of Congress, Internet Archive "
        "and the rest."
    )

    st.divider()

    # ---------------------------------------------------------------
    st.markdown("#### Watermark")
    st.caption(
        "A corner watermark is cropped off in seconds, so this one drifts "
        "across the frame and bounces off the edges. It steers around the "
        "caption band so the text stays readable."
    )
    col_a, col_b = st.columns(2)
    updated["WATERMARK_HANDLE"] = col_a.text_input(
        "Your handle", value=values.get("WATERMARK_HANDLE", ""),
        placeholder="KingSabzal", help="The @ is added if you leave it out.",
    )
    watermark_on = col_a.checkbox(
        "On by default for new videos",
        value=str(values.get("WATERMARK", "off")).lower() in ("on", "true"),
    )
    updated["WATERMARK"] = "on" if watermark_on else "off"
    updated["WATERMARK_OPACITY"] = str(col_b.slider(
        "Opacity", 0.05, 1.0, float(values.get("WATERMARK_OPACITY", "0.28") or 0.28),
        0.01, help="Low on purpose: a loud watermark costs more views than "
                   "the credit is worth.",
    ))
    updated["WATERMARK_SIZE"] = str(col_b.slider(
        "Size", 12, 120, int(values.get("WATERMARK_SIZE", "34") or 34)))
    updated["WATERMARK_SPEED"] = str(col_b.slider(
        "Drift speed", 5, 400, int(values.get("WATERMARK_SPEED", "60") or 60)))

    st.divider()

    # ---------------------------------------------------------------
    st.markdown("#### Defaults for new videos")
    st.caption("Starting points on the Create tab. Change them per video there.")
    with st.expander("Captions, audio and rendering"):
        for key in ["CAPTION_SAFE_ZONE", "CAPTION_FONT_SIZE", "CAPTION_FONT_COLOR",
                    "CAPTION_STROKE_WIDTH", "CAPTION_STROKE_COLOR",
                    "CAPTION_FONT_FACE", "CAPTION_FONT_FILE", "EMOJI_FONT_FILE",
                    "TTS_PROVIDER", "STT_PROVIDER"]:
            spec = settings_store.SCHEMA[key]
            if spec.get("kind") == "bool":
                on = str(values.get(key, "")).lower() in ("on", "true", "1", "yes")
                updated[key] = "on" if st.checkbox(
                    spec["label"], value=on, key=f"set_{key}") else "off"
            else:
                updated[key] = st.text_input(
                    spec["label"], value=values.get(key, ""), key=f"set_{key}")

    if st.button("Save settings", type="primary"):
        settings_store.write(updated)
        st.success("Saved.")
        still = settings_store.missing_settings()
        if still:
            st.warning("Still required before a run: " + ", ".join(still))
        else:
            st.info("Everything needed is set. The Create tab is ready.")
