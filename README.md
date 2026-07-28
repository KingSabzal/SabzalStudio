# SabzalStudio

Turn an idea, a trend or a link into a finished short-form video, with the
narration, the footage, the music, the captions and the upload packages all
produced for you.

Nothing here costs money. Every source is free, and no paid API is used
anywhere in the pipeline. (The one caveat is the optional Remotion renderer,
which carries its own licence for larger companies — see [Licence](#licence).
The default renderer does not.)

---

## Three ways to make a video

**Manual.** You choose everything: the topic, the script style, the length,
portrait or landscape, the narrator, the caption preset, whether emoji appear,
whether ambient effects play, and whether your handle drifts across the frame.

**Trends.** Nine sources are scanned for what is trending right now, and the
model proposes ten to fifteen titles built on them. Each is scored on
curiosity, emotional pull, shareability, search potential and how crowded the
subject already is. Pick one and it runs. Every setting was decided from the
trend, so you choose nothing.

**From a link.** Paste a news article or a Wikipedia page. The article body is
separated from the navigation and advertising around it, the substance is
measured, the facts, numbers, names and quotes are pulled out, and every
setting is derived from what the article turns out to be. Again you choose
nothing.

---

## What comes out

For each video:

* the rendered file, named after the title it will be uploaded with
  (`Scientists-Found-a-Creature-That-Glows.mp4`)
* a YouTube package: title plus five alternatives to A/B test, a Shorts title,
  a full description, tags, chapters and a pinned comment
* an Instagram package: a hook sized to the 125-character cut-off, a caption,
  at most five hashtags, and alt text
* a TikTok package: a caption front-loaded into the 80 visible characters,
  hashtags and a sound suggestion
* a complete thumbnail brief, written to 2026 rules, ready to paste into any
  image model

Everything the model returns is measured against each platform's real limits
and corrected before it is written out. Corrections are listed rather than
applied silently, so you can see what was changed.

---

## Install

Python 3.10, 3.11 or 3.12. Not 3.13 yet: two of the transcription
dependencies publish no wheels for it.

```bash
pip install -r requirements.txt
streamlit run app.py
```

**ImageMagick is needed for captions**, and it is the one thing pip cannot
install for you. Without it the video still renders, but with no text on it.

| | |
|---|---|
| Debian / Ubuntu | `sudo apt install imagemagick` |
| Fedora | `sudo dnf install ImageMagick` |
| macOS | `brew install imagemagick` |
| Windows | <https://imagemagick.org/script/download.php#windows> — tick **Install legacy utilities** |

ffmpeg is not a separate install. A copy is bundled and put on the path on
first run.

Open the **Settings** tab and add two things:

1. **A Pexels key.** Free from <https://www.pexels.com/api/new/>.
2. **An AI provider.** One of four: 9Router, OpenRouter, NVIDIA NIM or
   Cloudflare Workers AI.

A Pixabay key is optional but worth adding, since it widens the media search
considerably.

Full instructions, including Windows, are in [SETUP.md](SETUP.md) and
[INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).

---

## The seven stages

Every stage writes a checkpoint. An interrupted run resumes from where it
stopped instead of starting over, and changing the topic starts fresh.

| | Stage | What happens |
|---|---|---|
| 1 | Script | Written to one of 30 styles, at 140 words a minute |
| 2 | Voiceover | One of 47 voices, with per-sentence emotion and real pauses |
| 3 | Captions | Whisper transcribes locally, giving word-level timings |
| 4 | Music and effects | A track matched to the style, plus effects placed where the narration earns them |
| 5 | Footage | One clip per timed segment, searched across every free source |
| 6 | Render | Captions, watermark and a properly mixed audio track |
| 7 | Upload packages | The metadata above, plus the thumbnail brief |

---

## Why it looks and sounds the way it does

**Captions.** 27 presets, from the plain white default to the one-word
Hormozi style, karaoke highlighting and genre looks for true crime, finance
and documentary. Ten fonts are committed to the repository, so a preset looks
the same on every machine. Captions sit at bottom centre, inside the safe zone
that all three platforms share, so nothing is ever hidden behind a subscribe
button.

**Audio.** The music is ducked under the voice by a sidechain compressor, the
800 Hz and 2 kHz range is carved out of the music so speech stays intelligible
through it, and the finished track is normalised to -14 LUFS with a -1.5 dBTP
ceiling. Measured, not assumed.

**Watermark.** A corner watermark is cropped off in seconds, so this one never
stops moving. It drifts across the frame, bounces off the edges, and steers
around the caption band so the text stays readable.

**Downloads never skip.** A missing clip would leave a black flash exactly
where the narration is still talking. So every download retries, resumes with
HTTP Range requests, and rotates through a pool of 519 real browser user
agents. If a clip still cannot be fetched, the run stops with an error rather
than producing a broken video. The checkpoint is saved, so nothing is lost.

---

## Where the media comes from

37 sources, all CC0, Public Domain, Pexels, Pixabay or Mixkit licensed, so
nothing in a finished video needs a credit.

| | Sources |
|---|---|
| Video | Pexels, Pixabay, Mixkit, Coverr, Dareful, Internet Archive, Openverse and more |
| Images | NASA, the Met, Smithsonian, Wikimedia Commons, Library of Congress, Flickr Commons, NOAA, USGS, the National Park Service |
| Music | Pixabay, Mixkit, Openverse, Wikimedia Audio |
| Effects | Pixabay, Mixkit, Freesound |

Each entry records whether it answered when last checked, so the **Media
sources** view shows what is actually carrying the work rather than a
decorative list.

---

## Licence

MIT. See [LICENSE](LICENSE).

One exception worth knowing about. The default renderer is MoviePy and is
covered by the above. The optional **Remotion** renderer is not MIT: Remotion
is free for individuals, non-profits and small companies, but a for-profit
organisation above their size threshold needs a paid company licence. See
<https://remotion.dev/license>. Nothing in the default path touches it, and
the ten bundled fonts are OFL 1.1 except Noto Color Emoji, which is Apache 2.0
— all of them redistributable, including inside a rendered video.
