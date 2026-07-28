"""Stage 7: writes the upload packages for YouTube, Instagram and TikTok.

The pipeline finishes with a rendered file and nothing to publish it with.
This closes that gap: one LLM call produces a title, description, tags,
captions and hashtags for all three platforms, and the result is then checked
against the platforms' real 2026 limits rather than trusted as written.

Two things matter about the design:

* The LLM is asked once, not three times. A separate call per platform costs
  three times as long and produces packages that contradict each other.
* Whatever comes back is post-processed. A model will happily return eight
  Instagram hashtags when Instagram blocks anything over five, or a 140
  character title when YouTube truncates at 100. The checks here are what make
  the output safe to paste into an upload form.

If the LLM is unreachable the stage still produces a usable package built from
the script itself, because a video with no metadata cannot be published at all.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from utility.llm.llm_router import extract_json
from utility.publishing.platform_standards import (
    INSTAGRAM,
    TIKTOK,
    YOUTUBE,
    check_policy_risks,
    front_load_check,
    select_hashtags,
)
from utility.publishing.thumbnail_prompt import build_prompt as build_thumbnail_prompt

WORDS_PER_MINUTE = 140

PROMPT = """Write complete upload packages for this video, following 2026 SEO practice.

TOPIC: {topic}
VIDEO STYLE: {style}
DURATION: {duration} seconds ({format_label})
SCRIPT:
\"\"\"{script}\"\"\"

Rules:
- YouTube title: under {yt_title_max} characters, built around one primary
  keyword, opening a curiosity gap. Give 5 alternatives that each use a
  DIFFERENT angle so they can be A/B tested.
- "shorts_title": a shorter version under 60 characters for the Shorts feed.
- "primary_keyword": the single keyword the title is built around.
- YouTube description: {yt_desc_min}-{yt_desc_max} characters. The first two
  lines are a hook and a summary, because only {yt_visible} characters show
  before the fold. Then key points, then a subscribe line, then 3-5 hashtags.
- 10-15 YouTube tags. Tags lost most of their ranking weight after 2019, so a
  focused set beats a long one. Include some long-tail phrases.
- "thumbnail_text": {thumb_min}-{thumb_max} words, bold and emotional. It must
  NOT repeat the title word for word; it complements it.
- Instagram caption: the first {ig_visible} characters must carry the hook AND
  the primary keyword, because that is where Instagram truncates. Then 400-1200
  characters of substance.
- Instagram hashtags: EXACTLY {ig_tags} or fewer. Instagram enforced a hard cap
  in December 2025 and strips or blocks anything above it. Use specific
  descriptive tags. Never #fyp, #viral, #love or #instagood: they are on
  billions of posts and give the algorithm no information.
- Instagram alt text for accessibility, under {ig_alt} characters.
- TikTok caption: 50-150 characters. Only about {tt_visible} characters show in
  the feed, so front-load the hook. Include the topic keyword naturally.
- TikTok hashtags: 3-5 specific tags. Do NOT include #fyp or #viral: TikTok has
  confirmed they do not push content to the For You feed.
- All output in English.

Return strictly this JSON and nothing else:
{{
 "youtube": {{"title": "...", "alt_titles": ["...","...","...","...","..."],
   "shorts_title": "...", "primary_keyword": "...", "description": "...",
   "tags": ["..."], "thumbnail_text": "...", "pinned_comment": "...",
   "chapters": [{{"time": "0:00", "label": "..."}}], "keywords": ["..."]}},
 "instagram": {{"hook_line": "...", "caption": "...", "hashtags": ["..."],
   "cover_text": "...", "alt_text": "..."}},
 "tiktok": {{"hook_line": "...", "caption": "...", "hashtags": ["..."],
   "cover_text": "...", "sound_suggestion": "..."}}
}}
"""


def _extract_json(text: str) -> Optional[Any]:
    """Pull a JSON object out of an LLM reply.

    Models wrap JSON in prose or code fences often enough that parsing the raw
    string fails regularly.

    This used to slice between the first '{' and the last '}', which broke on
    the two things models actually do: adding a closing sentence after the JSON,
    and returning two objects in a row. Both leave a trailing fragment inside
    the slice, so json.loads raises and the caller falls back to a keyword-built
    package -- silently, so the user never learns the model output was discarded.

    utility.llm.llm_router.extract_json handles both cases: it tracks brace
    depth, collects every balanced candidate, tries the longest first and
    repairs trailing commas. One parser, used everywhere.
    """
    if not text:
        return None
    return extract_json(text)


def _trim(text: str, limit: int) -> str:
    """Cut to a hard limit on a word boundary where possible."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    return (cut[:space] if space > limit * 0.6 else cut).rstrip(" ,.;:-")


def _topic_words(topic: str, script: str) -> List[str]:
    words = re.findall(r"[a-z]{4,}", f"{topic} {script}".lower())
    seen, out = set(), []
    for word in words:
        if word not in seen:
            seen.add(word)
            out.append(word)
    return out[:30]


class MetadataGenerator:
    """Builds and validates the three upload packages."""

    def __init__(self, config=None):
        from utility.config import get_config
        self.config = config or get_config()

    # ------------------------------------------------------------------
    def generate(self, topic: str, script: str, style_name: str,
                 duration_seconds: float = 0.0) -> Dict[str, Any]:
        """Produce the full metadata package for one video."""
        duration = duration_seconds or (
            len(script.split()) / WORDS_PER_MINUTE * 60
        )
        format_label = "Shorts / Reel / TikTok" if duration < 120 else "long form"

        data = self._ask_llm(topic, script, style_name, duration, format_label)
        if not data:
            print("[metadata] The model did not return usable JSON. "
                  "Building a package from the script instead.")
            data = self._fallback(topic, script)

        return self._post_process(data, topic, script, style_name, duration,
                                  format_label)

    # ------------------------------------------------------------------
    def _ask_llm(self, topic, script, style_name, duration, format_label):
        prompt = PROMPT.format(
            topic=topic, style=style_name, script=script,
            duration=int(duration), format_label=format_label,
            yt_title_max=YOUTUBE["title_max"],
            yt_desc_min=YOUTUBE["description_target"][0],
            yt_desc_max=YOUTUBE["description_target"][1],
            yt_visible=YOUTUBE["description_visible"],
            thumb_min=2, thumb_max=5,
            ig_visible=INSTAGRAM["caption_visible"],
            ig_tags=INSTAGRAM["hashtag_hard_cap"],
            ig_alt=INSTAGRAM["alt_text_max"],
            tt_visible=TIKTOK["caption_visible"],
        )
        # A `provider == "gemini"` branch used to sit here; 'gemini' is not one
        # of the four providers the config accepts, so it was unreachable.
        try:
            client = self.config.get_llm_client()
            model = self.config.get_llm_model()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",
                     "content": "You write publishing metadata and return only JSON."},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response.choices[0].message.content
        except Exception as error:
            print(f"[metadata] The model call failed: {error}")
            return None

        data = _extract_json(raw)
        if data is None:
            # Say what came back. Returning None silently sends the caller to
            # the keyword-built fallback, and the user is left wondering why
            # their title reads like a machine wrote it -- because it did, but
            # not the one they configured.
            preview = " ".join(str(raw or "").split())[:160]
            print(f"[metadata] The reply contained no usable JSON. "
                  f"It began: {preview!r}")
        return data

    # ------------------------------------------------------------------
    def _fallback(self, topic: str, script: str) -> Dict[str, Any]:
        """A usable package built from the script, with no model involved."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
        hook = sentences[0] if sentences else topic
        body = " ".join(sentences[:6])
        words = _topic_words(topic, script)
        return {
            "youtube": {
                "title": _trim(hook, YOUTUBE["title_max"]),
                "alt_titles": [],
                "shorts_title": _trim(hook, 60),
                "primary_keyword": words[0] if words else topic,
                "description": f"{hook}\n\n{body}\n\nSubscribe for more.",
                "tags": words[:12],
                "thumbnail_text": " ".join(hook.split()[:4]),
                "pinned_comment": "What surprised you most about this?",
                "chapters": [],
                "keywords": words[:10],
            },
            "instagram": {
                "hook_line": _trim(hook, INSTAGRAM["caption_visible"]),
                "caption": f"{hook}\n\n{body}",
                "hashtags": words[:5],
                "cover_text": " ".join(hook.split()[:4]),
                "alt_text": _trim(topic, INSTAGRAM["alt_text_max"]),
            },
            "tiktok": {
                "hook_line": _trim(hook, TIKTOK["caption_visible"]),
                "caption": _trim(hook, 150),
                "hashtags": words[:4],
                "cover_text": " ".join(hook.split()[:4]),
                "sound_suggestion": "A trending sound that matches the pace.",
            },
        }

    # ------------------------------------------------------------------
    def _post_process(self, data, topic, script, style_name, duration,
                      format_label) -> Dict[str, Any]:
        """Enforce every platform limit and attach the compliance report.

        This is the part that makes the output trustworthy. A model asked for
        five hashtags will sometimes return eight, and a title asked to be
        under 100 characters will sometimes be 130. Rather than hoping, every
        field is measured and corrected here, and what was corrected is
        recorded so it is visible rather than silent.
        """
        youtube = dict(data.get("youtube") or {})
        instagram = dict(data.get("instagram") or {})
        tiktok = dict(data.get("tiktok") or {})
        corrections: List[str] = []

        # --- YouTube -------------------------------------------------
        title = str(youtube.get("title") or topic)
        if len(title) > YOUTUBE["title_max"]:
            corrections.append(
                f"YouTube title was {len(title)} characters; trimmed to "
                f"{YOUTUBE['title_max']}."
            )
            title = _trim(title, YOUTUBE["title_max"])
        youtube["title"] = title

        description = str(youtube.get("description") or "")
        if len(description) > YOUTUBE["description_max"]:
            corrections.append(
                f"YouTube description was {len(description)} characters; "
                f"trimmed to {YOUTUBE['description_max']}."
            )
            description = _trim(description, YOUTUBE["description_max"])
        youtube["description"] = description

        tags = [str(t).strip() for t in (youtube.get("tags") or []) if str(t).strip()]
        if len(tags) > YOUTUBE["tags_hard_max"]:
            corrections.append(
                f"YouTube had {len(tags)} tags; kept the first "
                f"{YOUTUBE['tags_hard_max']}."
            )
            tags = tags[:YOUTUBE["tags_hard_max"]]
        # YouTube also caps the combined tag string at 500 characters.
        total, kept = 0, []
        for tag in tags:
            if total + len(tag) + 1 > YOUTUBE["tags_total_chars"]:
                corrections.append(
                    "YouTube tags exceeded the 500 character total; "
                    "the overflow was dropped."
                )
                break
            kept.append(tag)
            total += len(tag) + 1
        youtube["tags"] = kept

        # --- Instagram -----------------------------------------------
        caption = str(instagram.get("caption") or "")
        if len(caption) > INSTAGRAM["caption_max"]:
            corrections.append(
                f"Instagram caption was {len(caption)} characters; trimmed to "
                f"{INSTAGRAM['caption_max']}."
            )
            caption = _trim(caption, INSTAGRAM["caption_max"])
        instagram["caption"] = caption

        topic_words = _topic_words(topic, script)
        ig_tags, ig_notes = select_hashtags(
            instagram.get("hashtags") or [], "instagram", topic_words
        )
        if len(instagram.get("hashtags") or []) > INSTAGRAM["hashtag_hard_cap"]:
            corrections.append(
                f"Instagram returned {len(instagram['hashtags'])} hashtags. "
                f"Instagram blocks anything over {INSTAGRAM['hashtag_hard_cap']}, "
                f"so the list was cut."
            )
        instagram["hashtags"] = ig_tags
        instagram["hashtag_notes"] = ig_notes

        alt = str(instagram.get("alt_text") or "")
        if len(alt) > INSTAGRAM["alt_text_max"]:
            alt = _trim(alt, INSTAGRAM["alt_text_max"])
            corrections.append("Instagram alt text was trimmed to 100 characters.")
        instagram["alt_text"] = alt

        # --- TikTok --------------------------------------------------
        tt_caption = str(tiktok.get("caption") or "")
        if len(tt_caption) > TIKTOK["caption_max"]:
            tt_caption = _trim(tt_caption, TIKTOK["caption_max"])
            corrections.append("TikTok caption was trimmed to 4000 characters.")
        tiktok["caption"] = tt_caption

        tt_tags, tt_notes = select_hashtags(
            tiktok.get("hashtags") or [], "tiktok", topic_words
        )
        tiktok["hashtags"] = tt_tags
        tiktok["hashtag_notes"] = tt_notes

        # --- Checks that inform rather than change -------------------
        report = {
            "youtube_title_length": len(youtube["title"]),
            "youtube_description_length": len(youtube["description"]),
            "youtube_tag_count": len(youtube["tags"]),
            "instagram_caption_length": len(instagram["caption"]),
            "instagram_hashtag_count": len(instagram["hashtags"]),
            "tiktok_caption_length": len(tiktok["caption"]),
            "tiktok_hashtag_count": len(tiktok["hashtags"]),
            "instagram_front_load": front_load_check(
                instagram["caption"], INSTAGRAM["caption_visible"]
            ),
            "tiktok_front_load": front_load_check(
                tiktok["caption"], TIKTOK["caption_visible"]
            ),
            "policy_risks": [
                risk.as_dict() if hasattr(risk, "as_dict") else risk
                for risk in check_policy_risks(
                    youtube["title"], youtube["description"], script
                )
            ],
            "corrections_applied": corrections,
        }

        # --- Thumbnail brief -----------------------------------------
        thumbnail = build_thumbnail_prompt(
            topic=topic,
            style_name=style_name,
            thumbnail_text=youtube.get("thumbnail_text", ""),
            title=youtube["title"],
            script=script,
        )
        youtube["thumbnail_text"] = thumbnail["text"]

        return {
            "topic": topic,
            "style": style_name,
            "duration_seconds": round(duration, 1),
            "format": format_label,
            "youtube": youtube,
            "instagram": instagram,
            "tiktok": tiktok,
            "thumbnail": thumbnail,
            "report": report,
        }


# ----------------------------------------------------------------------
def to_text(package: Dict[str, Any]) -> str:
    """The package as a readable text file, ready to copy from."""
    youtube = package.get("youtube", {})
    instagram = package.get("instagram", {})
    tiktok = package.get("tiktok", {})
    report = package.get("report", {})
    lines: List[str] = []

    def rule(title: str) -> None:
        lines.extend(["", "=" * 66, title, "=" * 66])

    lines.append(f"UPLOAD PACKAGES  -  {package.get('topic', '')}")
    lines.append(f"Style: {package.get('style')}   "
                 f"Duration: {package.get('duration_seconds')}s   "
                 f"Format: {package.get('format')}")

    rule("YOUTUBE")
    lines.append(f"Title ({report.get('youtube_title_length')}/100):")
    lines.append(f"  {youtube.get('title', '')}")
    if youtube.get("alt_titles"):
        lines.append("Alternatives to A/B test:")
        for alt in youtube["alt_titles"]:
            lines.append(f"  - {alt}")
    if youtube.get("shorts_title"):
        lines.append(f"Shorts title: {youtube['shorts_title']}")
    lines.append(f"Primary keyword: {youtube.get('primary_keyword', '')}")
    lines.append("")
    lines.append(f"Description ({report.get('youtube_description_length')} chars):")
    lines.append(youtube.get("description", ""))
    lines.append("")
    lines.append(f"Tags ({report.get('youtube_tag_count')}): "
                 f"{', '.join(youtube.get('tags', []))}")
    if youtube.get("chapters"):
        lines.append("Chapters:")
        for chapter in youtube["chapters"]:
            lines.append(f"  {chapter.get('time', '')}  {chapter.get('label', '')}")
    if youtube.get("pinned_comment"):
        lines.append(f"Pinned comment: {youtube['pinned_comment']}")

    rule("INSTAGRAM")
    lines.append(f"Hook (first {INSTAGRAM['caption_visible']} chars are what shows):")
    lines.append(f"  {instagram.get('hook_line', '')}")
    lines.append("")
    lines.append(f"Caption ({report.get('instagram_caption_length')} chars):")
    lines.append(instagram.get("caption", ""))
    lines.append("")
    lines.append(f"Hashtags ({report.get('instagram_hashtag_count')}/"
                 f"{INSTAGRAM['hashtag_hard_cap']} allowed): "
                 f"{' '.join(instagram.get('hashtags', []))}")
    for note in instagram.get("hashtag_notes", []):
        lines.append(f"  note: {note}")
    lines.append(f"Alt text: {instagram.get('alt_text', '')}")

    rule("TIKTOK")
    lines.append(f"Hook (first {TIKTOK['caption_visible']} chars are what shows):")
    lines.append(f"  {tiktok.get('hook_line', '')}")
    lines.append("")
    lines.append(f"Caption ({report.get('tiktok_caption_length')} chars):")
    lines.append(tiktok.get("caption", ""))
    lines.append("")
    lines.append(f"Hashtags: {' '.join(tiktok.get('hashtags', []))}")
    for note in tiktok.get("hashtag_notes", []):
        lines.append(f"  note: {note}")
    if tiktok.get("sound_suggestion"):
        lines.append(f"Sound: {tiktok['sound_suggestion']}")

    rule("THUMBNAIL")
    thumbnail = package.get("thumbnail", {})
    lines.append(thumbnail.get("prompt", ""))
    lines.append("")
    lines.append("NEGATIVE PROMPT")
    lines.append(thumbnail.get("negative_prompt", ""))
    lines.append("")
    lines.append("Checklist before uploading:")
    for item in thumbnail.get("checklist", []):
        lines.append(f"  [ ] {item}")

    if report.get("corrections_applied"):
        rule("CORRECTIONS APPLIED TO THE MODEL OUTPUT")
        for correction in report["corrections_applied"]:
            lines.append(f"  - {correction}")

    if report.get("policy_risks"):
        rule("POLICY RISKS")
        for risk in report["policy_risks"]:
            lines.append(f"  - {risk}")

    return "\n".join(lines)
