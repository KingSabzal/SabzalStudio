"""Settings kept in config.json, editable from the interface.

The project used to be configured only by hand-editing a .env file. That works
for a command line tool but not for a user interface: a browser form cannot
sensibly rewrite dotenv syntax, and a stray quote in a .env silently breaks
the whole run.

Settings now live in config.json. The file is plain JSON, so the interface can
read and write it safely, and a human can still open it and see what is set.

The awkward part of this change is that fifty places in the codebase already
read their setting with os.getenv, spread across the watermark, the emoji
bank, the caption renderer, the sound effects and the media sources. Rewriting
all of them at once would be a large, risky edit for no functional gain. So
this module loads config.json into the process environment at startup. Every
existing os.getenv call keeps working untouched, and reads the value the
interface wrote.

Precedence, highest first:

1. A real environment variable set in the shell. This is what makes
   `WATERMARK=on python app.py "topic"` work for a one-off run.
2. config.json, which is what the interface writes.
3. .env, still read if it exists, so an older install keeps running and can
   be migrated rather than broken.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional

CONFIG_FILENAME = "config.json"
EXAMPLE_FILENAME = "config.example.json"

_LOCK = threading.Lock()
_loaded = False


def project_root() -> str:
    """The directory holding config.json, which is the project root."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", ".."))


def config_path() -> str:
    return os.path.join(project_root(), CONFIG_FILENAME)


# Every setting the project understands, with its default. The interface
# builds its form from this, which is why it carries a group and a label
# rather than being a bare dictionary of values.
SCHEMA: Dict[str, Dict[str, Any]] = {
    # --- Provider -------------------------------------------------
    "LLM_PROVIDER": {"default": "openrouter", "group": "AI provider",
                     "label": "Provider", "kind": "choice",
                     "choices": ["9router", "openrouter", "nvidia", "cloudflare"]},
    "ROUTER9_URL": {"default": "http://localhost:9000/v1", "group": "AI provider",
                    "label": "9Router base URL"},
    "ROUTER9_KEY": {"default": "", "group": "AI provider",
                    "label": "9Router key", "secret": True},
    "OPENROUTER_API_KEY": {"default": "", "group": "AI provider",
                           "label": "OpenRouter key", "secret": True},
    "NVIDIA_NIM_KEY": {"default": "", "group": "AI provider",
                       "label": "NVIDIA NIM key", "secret": True},
    "NVIDIA_NIM_URL": {"default": "https://integrate.api.nvidia.com/v1",
                       "group": "AI provider", "label": "NVIDIA base URL"},
    "CLOUDFLARE_ACCOUNT_ID": {"default": "", "group": "AI provider",
                              "label": "Cloudflare account ID"},
    "CLOUDFLARE_API_TOKEN": {"default": "", "group": "AI provider",
                             "label": "Cloudflare API token", "secret": True},
    "LLM_MODEL": {"default": "", "group": "AI provider",
                  "label": "Model (blank picks one automatically)"},

    # --- Media keys -----------------------------------------------
    "PEXELS_API_KEY": {"default": "", "group": "Media",
                       "label": "Pexels key", "secret": True},
    "PIXABAY_API_KEY": {"default": "", "group": "Media",
                        "label": "Pixabay key (optional)", "secret": True},

    # --- Video ----------------------------------------------------
    "VIDEO_STYLE": {"default": "facts", "group": "Video", "label": "Script style"},
    "VIDEO_DURATION": {"default": "50", "group": "Video",
                       "label": "Target length in seconds"},
    "VIDEO_ORIENTATION": {"default": "portrait", "group": "Video",
                          "label": "Orientation", "kind": "choice",
                          "choices": ["portrait", "landscape"]},
    "RENDER_ENGINE": {"default": "moviepy", "group": "Video",
                      "label": "Renderer", "kind": "choice",
                      "choices": ["moviepy", "remotion"]},

    # --- Voice ----------------------------------------------------
    "TTS_PROVIDER": {"default": "edgetts", "group": "Voice", "label": "Engine"},
    "EDGETTS_VOICE": {"default": "auto", "group": "Voice", "label": "Voice"},
    "STT_PROVIDER": {"default": "whisper", "group": "Voice",
                     "label": "Transcription"},

    # --- Captions -------------------------------------------------
    "CAPTIONS_ENABLED": {"default": "true", "group": "Captions",
                         "label": "Show captions", "kind": "bool"},
    "CAPTION_STYLE": {"default": "auto", "group": "Captions", "label": "Style preset"},
    "CAPTION_SAFE_ZONE": {"default": "on", "group": "Captions",
                          "label": "Keep clear of platform buttons", "kind": "bool"},
    "CAPTION_EMOJI": {"default": "off", "group": "Captions",
                      "label": "Emoji in captions", "kind": "bool"},
    "CAPTION_EMOJI_PER_MINUTE": {"default": "10", "group": "Captions",
                                 "label": "Emoji per minute"},
    "CAPTION_FONT_SIZE": {"default": "", "group": "Captions",
                          "label": "Font size override"},
    "CAPTION_FONT_COLOR": {"default": "", "group": "Captions",
                           "label": "Colour override"},
    "CAPTION_STROKE_WIDTH": {"default": "", "group": "Captions",
                             "label": "Outline width override"},
    "CAPTION_STROKE_COLOR": {"default": "", "group": "Captions",
                             "label": "Outline colour override"},
    "CAPTION_FONT_FACE": {"default": "", "group": "Captions",
                          "label": "Font family override"},
    "CAPTION_FONT_FILE": {"default": "", "group": "Captions",
                          "label": "Font file path override"},
    "EMOJI_FONT_FILE": {"default": "", "group": "Captions",
                        "label": "Emoji font path override"},

    # --- Audio ----------------------------------------------------
    "SFX_ENABLED": {"default": "true", "group": "Audio",
                    "label": "Ambient sound effects", "kind": "bool"},
    "SFX_DENSITY": {"default": "medium", "group": "Audio",
                    "label": "Effect density", "kind": "choice",
                    "choices": ["low", "medium", "high"]},

    # --- Watermark ------------------------------------------------
    "WATERMARK": {"default": "off", "group": "Watermark",
                  "label": "Show handle watermark", "kind": "bool"},
    "WATERMARK_HANDLE": {"default": "", "group": "Watermark", "label": "Handle"},
    "WATERMARK_OPACITY": {"default": "0.28", "group": "Watermark", "label": "Opacity"},
    "WATERMARK_SIZE": {"default": "34", "group": "Watermark", "label": "Size"},
    "WATERMARK_SPEED": {"default": "60", "group": "Watermark",
                        "label": "Drift speed"},
}

GROUPS = ["AI provider", "Media", "Video", "Voice", "Captions", "Audio", "Watermark"]


def defaults() -> Dict[str, str]:
    """Every setting at its default value."""
    return {key: str(spec["default"]) for key, spec in SCHEMA.items()}


def read() -> Dict[str, str]:
    """The saved settings, or the defaults when nothing is saved yet."""
    path = config_path()
    values = defaults()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                saved = json.load(handle)
            if isinstance(saved, dict):
                for key, value in saved.items():
                    if key in SCHEMA:
                        values[key] = "" if value is None else str(value)
        except (OSError, json.JSONDecodeError) as error:
            print(f"[settings] Could not read {CONFIG_FILENAME} ({error}); "
                  f"using defaults.")
    return values


def write(values: Dict[str, Any]) -> str:
    """Save settings and apply them to this process straight away."""
    current = read()
    for key, value in values.items():
        if key in SCHEMA:
            current[key] = "" if value is None else str(value)

    path = config_path()
    with _LOCK:
        # Write to a temporary file and move it into place, so an interrupted
        # save cannot leave a half-written config behind.
        temporary = f"{path}.tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(current, handle, indent=2, ensure_ascii=False, sort_keys=True)
        os.replace(temporary, path)

    for key, value in current.items():
        if value != "":
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
    return path


def _load_dotenv_values() -> Dict[str, str]:
    """Read a .env, if one is still present, without importing dotenv."""
    path = os.path.join(project_root(), ".env")
    values: Dict[str, str] = {}
    if not os.path.exists(path):
        return values
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                # Trailing comments are common in the old example file.
                value = value.split(" #")[0].strip().strip("'\"")
                if key:
                    values[key] = value
    except OSError:
        pass
    return values


def apply(force: bool = False) -> Dict[str, str]:
    """Load settings into the environment so every os.getenv call sees them.

    Called once at startup. A variable already set in the real environment is
    never overwritten, so a one-off `WATERMARK=on python app.py ...` still
    wins over the saved configuration.
    """
    global _loaded
    if _loaded and not force:
        return read()

    shell_set = set(os.environ)
    dotenv_values = _load_dotenv_values()
    saved = read()
    has_config = os.path.exists(config_path())

    for key, value in {**dotenv_values, **({} if not has_config else saved)}.items():
        if key in shell_set:
            continue  # the shell wins
        if value == "":
            continue
        os.environ[key] = value

    # Anything only .env knows about, when there is no config.json yet.
    if not has_config:
        for key, value in dotenv_values.items():
            if key not in shell_set and value != "":
                os.environ.setdefault(key, value)

    # Seed anything still unset from the schema defaults, so a fresh install
    # with no config.json and no .env still has a working baseline. Without
    # this, settings that only ever had a default (the transcription engine,
    # the speech engine) arrive empty and validation rejects them.
    for key, value in defaults().items():
        if key not in os.environ and value != "":
            os.environ[key] = value

    _loaded = True
    return read()


def migrate_from_dotenv() -> Optional[str]:
    """Create config.json from an existing .env, once.

    Returns the path written, or None when there was nothing to migrate.
    """
    if os.path.exists(config_path()):
        return None
    values = _load_dotenv_values()
    if not values:
        return None
    known = {k: v for k, v in values.items() if k in SCHEMA}
    if not known:
        return None
    path = write(known)
    print(f"[settings] Migrated {len(known)} settings from .env into "
          f"{CONFIG_FILENAME}. The .env is no longer needed.")
    return path


def is_configured() -> bool:
    """Whether enough is set for a run to succeed."""
    values = read()
    if not values.get("PEXELS_API_KEY"):
        return False
    provider = values.get("LLM_PROVIDER", "")
    needed = {
        "9router": ["ROUTER9_URL"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "nvidia": ["NVIDIA_NIM_KEY", "NVIDIA_NIM_URL"],
        "cloudflare": ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"],
    }.get(provider, [])
    return all(values.get(field) for field in needed)


def missing_settings() -> list:
    """Which required settings are still empty, for a clear message."""
    values = read()
    missing = []
    if not values.get("PEXELS_API_KEY"):
        missing.append("PEXELS_API_KEY")
    provider = values.get("LLM_PROVIDER", "")
    needed = {
        "9router": ["ROUTER9_URL"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "nvidia": ["NVIDIA_NIM_KEY", "NVIDIA_NIM_URL"],
        "cloudflare": ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"],
    }.get(provider, [])
    missing += [f for f in needed if not values.get(f)]
    return missing
