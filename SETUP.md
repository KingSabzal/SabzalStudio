# Setting up SabzalStudio

## What you need

* **Python 3.10, 3.11 or 3.12.** Not 3.13: torch 2.3.1 and numpy 1.26.4, both
  required by the transcription stage, publish no wheels for it, so the install
  fails outright rather than degrading.
* **ImageMagick**, for drawing captions. See below.
* About 3 GB of disk space, mostly for Whisper's transcription model, which
  downloads itself the first time it runs
* An internet connection while a video is being made

ffmpeg is not a separate install. A copy is bundled and put on the path
automatically the first time you run anything.

## Install

```bash
pip install -r requirements.txt
```

### ImageMagick

Captions are drawn with ImageMagick, which pip cannot install. Without it
everything else still works and the video renders — with no text on it.

| | |
|---|---|
| Debian / Ubuntu | `sudo apt install imagemagick` |
| Fedora | `sudo dnf install ImageMagick` |
| Arch | `sudo pacman -S imagemagick` |
| macOS | `brew install imagemagick` |
| Windows | [imagemagick.org](https://imagemagick.org/script/download.php#windows), ticking **Install legacy utilities** |

Check it is visible:

```bash
magick -version     # ImageMagick 7
convert -version    # ImageMagick 6
```

If your distribution ships a security policy that blocks MoviePy's usual way of
passing text, the renderer notices on the first caption and switches to calling
ImageMagick directly. You do not have to do anything; a line in the log says so.

### Node.js — only for the optional Remotion renderer

The default renderer is MoviePy and needs nothing extra. If you switch
**Renderer** to `remotion` on the Create tab you also need
[Node.js 18 or newer](https://nodejs.org/); the first render then installs the
composer's npm packages, which takes a few minutes.

Remotion is not MIT-licensed. It is free for individuals, non-profits and small
companies; larger for-profit organisations need a paid licence. See
<https://remotion.dev/license>.

## Start

```bash
streamlit run app.py
```

That opens the interface in your browser. Everything is done from there.

## Configure

Everything is set from the **Settings** tab. There is no `.env` file; settings
are saved to `config.json`.

### 1. A Pexels key (required)

Free, takes a minute: <https://www.pexels.com/api/new/>

Pexels is the first place a clip is searched for and usually the best match.

### 2. An AI provider (required)

Pick one and give it its credentials.

| Provider | What you need | Where to get it |
|---|---|---|
| **9Router** | the base URL of your local install | your own machine |
| **OpenRouter** | an API key | <https://openrouter.ai/keys> |
| **NVIDIA NIM** | an API key | <https://build.nvidia.com/> |
| **Cloudflare Workers AI** | account ID and API token | <https://dash.cloudflare.com/profile/api-tokens> |

No model is configured. The provider is asked what it offers and the run works
down that list, so a model that is busy or withdrawn never stops a video.

Press **Test the connection** to confirm the credentials before generating
anything.

### 3. A Pixabay key (optional, recommended)

Free from <https://pixabay.com/api/key/>. It adds a second large library of
video, photos, music and sound effects, which makes a missing clip much less
likely.

Every other source needs no key at all: Mixkit, Coverr, Openverse, Wikimedia,
NASA, the Met, Library of Congress, Internet Archive and the rest.

### 4. Your handle (optional)

If you want the drifting watermark, put your handle in Settings. The `@` is
added for you.

---

## The interface

Five tabs.

**Manual** — you choose everything for one video: topic, style, length,
portrait or landscape, narrator, caption preset, emoji, sound effects and
watermark. These apply to that run only and do not change your saved defaults.

**Trends** — scans nine sources for what is trending now (Google Trends,
Google News, BBC, Al Jazeera, Reddit, Hacker News, Product Hunt, YouTube and
X), then asks the model for ten to fifteen titles built on them. Each is
scored, and picking one starts a run whose every setting was decided from the
trend.

**From a link** — paste a news article or Wikipedia page. The article is read,
its substance measured, and every setting derived from it.

**Settings** — keys, provider and handle. Saved permanently.

**Gallery** — every finished video with its upload packages, ready to download
or delete.

Trend scanning and article fetching both rotate through a pool of 519 real
browser user agents, so a source that rate-limits one identity is retried with
another rather than skipped.

---

## Where things are written

```
outputs/
  Scientists-Found-a-Creature-That-Glows.mp4     the video
  Scientists-Found-a-Creature-That-Glows.txt     the upload packages
  gallery.json                                   what the Gallery tab reads
config.json                                      your settings and keys
pipeline_checkpoint.json                         the run in progress
```

`config.json` holds your keys, so it is excluded from version control.
`config.example.json` lists every setting with its default.

---

## Downloads never skip

A clip that fails to download is not skipped. A missing segment would leave a
black flash in the finished video exactly where the narration is still
speaking, so instead:

* every download retries with exponential backoff and resumes with HTTP Range
  requests
* requests rotate through 519 real browser user agents
* when a segment finds nothing, the search widens to plainer terms and then
  reuses an earlier clip rather than leaving a gap
* if a clip still cannot be fetched, the run **stops with an error** instead of
  rendering a broken video

Stopping is safe. The checkpoint is saved, so running the same topic again
resumes from the stage that failed. Check your connection first, and add the
free Pixabay key if you have not.

---

## The seven stages

Each stage saves a checkpoint, so an interrupted run resumes rather than
starting over. Changing the topic starts fresh.

1. **Script** — one of 30 styles, at 140 words a minute
2. **Voiceover** — one of 47 voices, with per-sentence emotion and real pauses
3. **Timed captions** — Whisper transcribes locally, no account needed
4. **Music and sound effects** — matched to the style, placed where earned
5. **Footage** — one clip per segment across every free source
6. **Render** — captions, watermark, and a properly mixed audio track
7. **Upload packages** — YouTube, Instagram, TikTok, plus a thumbnail brief

---

## If something goes wrong

**"Missing PEXELS_API_KEY"** — add it on the Settings tab.

**The provider test fails** — check the key, and for Cloudflare check that the
token has the Workers AI permission.

**A run stops during Footage** — the connection dropped or the sources are
rate-limiting. Nothing is lost. Generate the same topic again and it resumes
from that stage. Adding a Pixabay key helps considerably.

**Captions look wrong** — an old `config.json` may have caption overrides set.
Clearing the override fields on the Settings tab restores the preset.

**Whisper is slow the first time** — it is downloading its model. That happens
once.
