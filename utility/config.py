import os
from typing import Optional, Literal

from utility.core import settings_store

# Settings come from config.json, with a .env still honoured if one exists.
# Loading them into the environment here means every existing os.getenv call
# across the project keeps working unchanged.
settings_store.apply()


class ConfigurationError(Exception):
    pass


class Config:
    _instance: Optional['Config'] = None
    
    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._validate_configuration()
        
        self._llm_client = None
        self._router = None
        self._initialized = True
    
    def _validate_env_file(self) -> None:
        """Kept so older callers still work. Settings no longer need a .env."""
        return None

    def _validate_configuration(self) -> None:
        errors = []
        
        llm_provider = os.getenv('LLM_PROVIDER', '').lower()
        valid = ['9router', 'openrouter', 'nvidia', 'cloudflare']
        if llm_provider not in valid:
            errors.append(
                f"Invalid LLM_PROVIDER: '{llm_provider}'. Must be one of: "
                f"{', '.join(valid)}"
            )
        else:
            # Each provider needs its own fields. The model itself is not
            # configured: the router discovers what the provider offers and
            # falls back through them automatically.
            required = {
                '9router': [('ROUTER9_URL', '9Router base URL')],
                'openrouter': [('OPENROUTER_API_KEY', 'OpenRouter API key')],
                'nvidia': [('NVIDIA_NIM_KEY', 'NVIDIA NIM API key'),
                           ('NVIDIA_NIM_URL', 'NVIDIA NIM base URL')],
                'cloudflare': [('CLOUDFLARE_ACCOUNT_ID', 'Cloudflare account ID'),
                               ('CLOUDFLARE_API_TOKEN', 'Cloudflare API token')],
            }[llm_provider]
            for key, label in required:
                if not os.getenv(key):
                    errors.append(
                        f"Missing {label}: set {key} (required for "
                        f"LLM_PROVIDER={llm_provider})"
                    )
        
        if not os.getenv('PEXELS_API_KEY'):
            errors.append(
                "Missing required API key: PEXELS_API_KEY. It is free from "
                "https://www.pexels.com/api/new/ . The other stock sources need "
                "no key, but Pexels is the first and best match for most clips."
            )
        
        stt_provider = os.getenv('STT_PROVIDER', '').lower()
        # Whisper is the only provider. It runs locally and costs nothing.
        # Deepgram was removed because it is a paid API.
        if stt_provider not in ['whisper']:
            errors.append(
                f"Invalid STT_PROVIDER: '{stt_provider}'. Only 'whisper' is supported."
            )
        
        tts_provider = os.getenv('TTS_PROVIDER', '').lower()
        # EdgeTTS is the only provider. It is free, and EDGETTS_VOICE may be
        # left at 'auto' so a voice is chosen from the script style.
        if tts_provider not in ['edgetts']:
            errors.append(
                f"Invalid TTS_PROVIDER: '{tts_provider}'. Only 'edgetts' is supported."
            )
        
        if errors:
            error_message = "Configuration validation failed:\n\n"
            for error in errors:
                error_message += f"  - {error}\n"
            error_message += ("\nOpen the Settings tab (streamlit run app.py) or edit "
                              "config.json directly.")
            raise ConfigurationError(error_message)
    
    def get_llm_provider(self) -> Literal['9router', 'openrouter', 'nvidia', 'cloudflare']:
        return os.getenv('LLM_PROVIDER', '').lower()
    
    def get_llm_model(self) -> str:
        """The model in use.

        Normally blank: the router discovers what the provider actually offers
        and works down that list, so a model that is busy or withdrawn does not
        stop the run. Setting LLM_MODEL pins one model instead.
        """
        pinned = os.getenv('LLM_MODEL', '').strip()
        if pinned:
            return pinned
        try:
            models = self.get_router().available_models()
            return models[0] if models else ''
        except Exception:
            return ''
    
    def get_router(self):
        """The model router for the selected provider."""
        if self._router is None:
            from utility.llm.llm_router import SmartLLMRouter
            self._router = SmartLLMRouter()
        return self._router
    
    def get_llm_client(self):
        """A client shaped like the OpenAI SDK, backed by the router.

        The script and search-query stages were written against
        ``client.chat.completions.create(...)``. Rather than rewrite those
        callers for four new providers, the router is wrapped in the same
        shape. They keep working, and they gain the router's automatic
        fallback between models for free.
        """
        if self._llm_client is None:
            from utility.llm.compat_client import RouterClient
            self._llm_client = RouterClient(self.get_router())
        return self._llm_client
    
    def get_stt_provider(self) -> Literal['whisper']:
        return os.getenv('STT_PROVIDER', 'whisper').lower()
    
    def get_tts_provider(self) -> Literal['edgetts']:
        return os.getenv('TTS_PROVIDER', 'edgetts').lower()

    def get_tts_voice(self) -> str:
        """The configured voice, or 'auto' to choose one from the script style."""
        return os.getenv('EDGETTS_VOICE', 'auto').strip()
    
    def get_pexels_api_key(self) -> str:
        key = os.getenv('PEXELS_API_KEY')
        if not key:
            raise ConfigurationError(
                "PEXELS_API_KEY is not set. It is free from "
                "https://www.pexels.com/api/new/ . Add it on the Settings tab."
            )
        return key
    
    def get_video_orientation(self) -> bool:
        """
        Returns True for landscape (horizontal) or False for portrait (vertical)
        Portrait (vertical, 1080x1920) is recommended for mobile platforms
        Landscape (horizontal, 1920x1080) is for traditional video
        """
        orientation = os.getenv('VIDEO_ORIENTATION', 'portrait').lower()
        if orientation not in ['portrait', 'landscape']:
            raise ConfigurationError(
                f"Invalid VIDEO_ORIENTATION: '{orientation}'. Must be 'portrait' or 'landscape'"
            )
        return orientation == 'landscape'

    def get_video_style(self) -> str:
        """The narrative style for the script.

        The original prompt was fixed to one style, so every video sounded the
        same. An unknown name is not fatal: the style module falls back to the
        original 'facts' behaviour and says so.
        """
        return os.getenv('VIDEO_STYLE', 'facts').strip().lower()

    def get_video_duration(self) -> int:
        """Target narration length in seconds.

        The original prompt asked for about 140 words regardless of anything, so
        every video came out the same length. The word count is now derived from
        this instead.
        """
        raw = os.getenv('VIDEO_DURATION', '50').strip()
        try:
            seconds = int(float(raw))
        except ValueError:
            raise ConfigurationError(
                f"Invalid VIDEO_DURATION: '{raw}'. Use a number of seconds, e.g. 50"
            )
        if not 10 <= seconds <= 900:
            raise ConfigurationError(
                f"VIDEO_DURATION is {seconds}s. Use a value between 10 and 900."
            )
        return seconds

    def get_pixabay_api_key(self) -> str:
        """The Pixabay key. Optional: the chain skips Pixabay when it is unset."""
        return os.getenv('PIXABAY_API_KEY', '').strip()

    def get_sfx_enabled(self) -> bool:
        """Whether ambient sound effects are placed under the narration."""
        return os.getenv('SFX_ENABLED', 'true').lower() == 'true'

    def get_sfx_density(self) -> str:
        """How many sound effects a minute: low (2), medium (5) or high (9)."""
        density = os.getenv('SFX_DENSITY', 'medium').lower().strip()
        if density not in ('low', 'medium', 'high'):
            print(f"[config] Unknown SFX_DENSITY '{density}'. Using 'medium'.")
            return 'medium'
        return density

    def get_captions_enabled(self) -> bool:
        """Get whether captions are enabled"""
        return os.getenv('CAPTIONS_ENABLED', 'true').lower() == 'true'

    def get_caption_font_size(self) -> int:
        """Get caption font size from config"""
        return int(os.getenv('CAPTION_FONT_SIZE', '100'))
    
    def get_caption_font_color(self) -> str:
        """Get caption font color from config"""
        return os.getenv('CAPTION_FONT_COLOR', 'white').lower()
    
    def get_caption_stroke_width(self) -> int:
        """Get caption stroke/outline width from config"""
        return int(os.getenv('CAPTION_STROKE_WIDTH', '3'))
    
    def get_caption_stroke_color(self) -> str:
        """Get caption stroke/outline color from config"""
        return os.getenv('CAPTION_STROKE_COLOR', 'black').lower()
    
    def get_caption_position(self) -> str:
        """Captions always sit at bottom centre.

        This is kept so any caller written against the old configuration
        still works. CAPTION_POSITION is no longer read: the four other
        positions the project used to offer all placed text somewhere a
        viewer does not look for it, or somewhere a platform button covers.
        """
        return 'bottom_center'

    def get_caption_font_face(self) -> str:
        """Get caption font face from config (e.g., Arial, Helvetica, Impact, Courier-New)"""
        return os.getenv('CAPTION_FONT_FACE', 'Arial-Bold')



def get_config() -> Config:
    try:
        return Config()
    except ConfigurationError as e:
        print(f"\n{'='*70}")
        print("ERROR: Configuration Failed")
        print('='*70)
        print(f"\n{str(e)}\n")
        print("Please fix these issues and try again.")
        print('='*70 + '\n')
        raise
