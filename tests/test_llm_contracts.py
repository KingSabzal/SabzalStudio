"""The contracts between the router and everything that calls it.

The bug these exist to prevent: ``RouterClient`` called
``router.complete(messages=...)`` while ``SmartLLMRouter.complete`` took a
``prompt`` and had no ``**kwargs``. Every call raised TypeError, which meant
stage 1 could never produce a script and the project could not make a video at
all. Nothing caught it because nothing exercised the two together.
"""

import pytest

from utility.llm.compat_client import RouterClient
from utility.llm.llm_router import CircuitBreaker, ModelEntry, SmartLLMRouter, extract_json


class FakeRouter(SmartLLMRouter):
    """A router that answers locally, so no network or credentials are needed."""

    def __init__(self, reply="ok"):
        self.breaker = CircuitBreaker()
        self._queue_cache = {}
        self.last_used_model = None
        self.reply = reply
        self.seen_messages = None
        self.seen_temperature = None

    @property
    def provider_id(self):
        return "openrouter"

    def build_queue(self, refresh=False):
        return [ModelEntry("openrouter", "fake-model", "http://localhost", "key")]

    def _call_model(self, entry, messages, temperature, max_tokens):
        self.seen_messages = messages
        self.seen_temperature = temperature
        return self.reply


def test_compat_client_reaches_the_router():
    """The OpenAI-shaped client must actually work against the real router."""
    router = FakeRouter(reply="a script")
    client = RouterClient(router)

    response = client.chat.completions.create(
        model="ignored",
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "the topic"},
        ],
    )

    assert response.choices[0].message.content == "a script"
    assert [m["role"] for m in router.seen_messages] == ["system", "user"]


def test_compat_client_passes_temperature_through():
    router = FakeRouter()
    RouterClient(router).chat.completions.create(
        model="m", messages=[{"role": "user", "content": "hi"}], temperature=0.3
    )
    assert router.seen_temperature == 0.3


def test_generate_content_reaches_the_router():
    router = FakeRouter(reply="text")
    assert RouterClient(router).generate_content("a prompt").text == "text"
    assert router.seen_messages == [{"role": "user", "content": "a prompt"}]


def test_complete_still_takes_a_prompt():
    """complete() keeps its original signature for its existing callers."""
    router = FakeRouter(reply="done")
    assert router.complete("the prompt", system="the system") == "done"
    assert router.seen_messages == [
        {"role": "system", "content": "the system"},
        {"role": "user", "content": "the prompt"},
    ]


def test_complete_messages_rejects_an_empty_list():
    with pytest.raises(ValueError):
        FakeRouter().complete_messages([])


@pytest.mark.parametrize(
    "reply,expected",
    [
        ('{"script": "plain"}', {"script": "plain"}),
        ('{"script": "He said {hi}"}', {"script": "He said {hi}"}),
        ('{"script": "ok"}\nHope this helps!', {"script": "ok"}),
        ('```json\n{"script": "fenced"}\n```', {"script": "fenced"}),
        ('{"script": "comma",}', {"script": "comma"}),
    ],
)
def test_extract_json_survives_what_models_actually_return(reply, expected):
    assert extract_json(reply) == expected


def test_extract_json_gives_up_cleanly():
    assert extract_json("no json here at all") is None
    assert extract_json("") is None
