"""SabzalStudio interface.

Started from the project root:

    streamlit run app.py
"""

from __future__ import annotations

import os
import sys

import streamlit as st

ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utility.core import settings_store  # noqa: E402

settings_store.apply()

from utility.ui import (  # noqa: E402
    create_tab, gallery_tab, settings_tab, trend_tab, url_tab,
)


def main() -> None:
    st.set_page_config(page_title="SabzalStudio", page_icon="🎬", layout="wide")
    st.title("SabzalStudio")
    st.caption(
        "Three ways to make a video. Seven checkpointed stages. "
        "Free sources only, no paid service anywhere."
    )

    if settings_store.missing_settings():
        st.warning(
            "Some required settings are still empty. Open **Settings** to "
            "finish setting up."
        )

    # Three ways to make a video: choose everything yourself, ride a trend, or
    # turn an article into one. The last two decide every setting themselves.
    manual, trend, from_url, settings, gallery = st.tabs(
        ["Manual", "Trends", "From a link", "Settings", "Gallery"]
    )
    with manual:
        create_tab.render()
    with trend:
        trend_tab.render()
    with from_url:
        url_tab.render()
    with settings:
        settings_tab.render()
    with gallery:
        gallery_tab.render()


main()
