"""Parsing the model's reply into a script.

The old parser sliced between the first '{' and the last '}'. That broke on the
two things models really do -- adding a sentence after the JSON, and returning
two objects -- and a break meant the whole run died at stage 1.
"""

import pytest

from utility.script.script_generator import (
    _script_from_reply,
    clean_markdown,
    words_for_duration,
)


@pytest.mark.parametrize(
    "reply,expected",
    [
        ('{"script": "plain text"}', "plain text"),
        ('{"script": "He said {hello} to me."}', "He said {hello} to me."),
        ('{"script": "ok"}\nHope this helps! {done}', "ok"),
        ('{"script": "one"}\n{"script": "two"}', "one"),
        ('Here you go:\n```json\n{"script": "fenced"}\n```', "fenced"),
        ('content: {"script": "prefixed"}', "prefixed"),
        ('{"script": "trailing comma",}', "trailing comma"),
        ('{"meta": {"a": 1}, "script": "nested"}', "nested"),
        ('  {"script": "  padded  "}  ', "padded"),
    ],
)
def test_reply_shapes_that_used_to_break_the_run(reply, expected):
    assert _script_from_reply(reply) == expected


@pytest.mark.parametrize(
    "reply",
    [
        "no json at all",
        '{"script": ""}',
        '{"script": "   "}',
        '{"other": "field"}',
        '["a", "b"]',
        "",
        None,
    ],
)
def test_unusable_replies_raise_rather_than_return_junk(reply):
    with pytest.raises(ValueError):
        _script_from_reply(reply)


def test_word_count_follows_the_requested_duration():
    assert words_for_duration(60) == 140
    assert words_for_duration(30) == 70
    # Never ask for so few words that the model cannot say anything.
    assert words_for_duration(1) == 20


def test_clean_markdown_keeps_the_narration_speakable():
    text = clean_markdown("**Bold** and _italic_ and `code` and [link](http://x)")
    assert "*" not in text and "_" not in text and "`" not in text
    assert "http://x" not in text
    assert "Bold" in text and "link" in text
