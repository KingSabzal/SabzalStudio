"""An OpenAI-SDK-shaped wrapper around the model router.

Two stages in this project were written against the OpenAI client:

    response = client.chat.completions.create(model=..., messages=[...])
    text = response.choices[0].message.content

Those stages are original project code and work well. Rather than rewrite them
for four new providers, this presents the router in the same shape. The
callers do not change, and they inherit the router's model discovery and
automatic fallback.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class _Message:
    def __init__(self, content: str):
        self.content = content
        self.role = "assistant"


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)
        self.finish_reason = "stop"
        self.index = 0


class _Response:
    """Mimics the parts of an OpenAI response the callers actually read."""

    def __init__(self, content: str, model: str = ""):
        self.choices = [_Choice(content)]
        self.model = model
        self.object = "chat.completion"


class _Completions:
    def __init__(self, router):
        self._router = router

    def create(self, model: Optional[str] = None,
               messages: Optional[List[Dict[str, str]]] = None,
               temperature: float = 1.0, max_tokens: int = 4096,
               **_ignored: Any) -> _Response:
        """Send a chat completion through the router.

        ``model`` is accepted and ignored on purpose. The router already knows
        which models the selected provider offers and works down that list, so
        naming one here would defeat the fallback that keeps a run alive when a
        model is busy or withdrawn.
        """
        text = self._router.complete_messages(
            messages or [],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _Response(text, model=getattr(self._router, "last_used_model", "") or "")


class _Chat:
    def __init__(self, router):
        self.completions = _Completions(router)


class RouterClient:
    """What ``config.get_llm_client()`` hands back."""

    def __init__(self, router):
        self._router = router
        self.chat = _Chat(router)

    @property
    def router(self):
        return self._router

    def generate_content(self, prompt: str):
        """Gemini-shaped entry point, kept because one caller still uses it."""
        text = self._router.complete_messages(
            [{"role": "user", "content": str(prompt)}]
        )

        class _GeminiLike:
            def __init__(self, value: str):
                self.text = value

        return _GeminiLike(text)
