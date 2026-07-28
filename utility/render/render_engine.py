import math
import os
import tempfile
import platform
import subprocess

# Must come before MoviePy: Pillow 10 removed the resampling constants that
# MoviePy 1.0.3 resizes with, and the caption clamp resizes on every render.
from utility.core import pillow_compat  # noqa: F401

from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip,
                            VideoFileClip)
from moviepy.video.fx.crop import crop
from moviepy.video.fx.freeze import freeze
from moviepy.video.fx.loop import loop
from utility.render.caption_renderer import (build_caption_clips,
                                             caption_style_from_env)
from utility.render.watermark import build as build_watermark
from moviepy.audio.fx.audio_loop import audio_loop
from utility.config import get_config

# The Remotion compositions in remotion-composer/ are all 30 fps. Matching them
# keeps the two render paths interchangeable.
OUTPUT_FPS = 30

def download_file(url, filename, kind="video"):
    """Download a file, retrying and resuming until it is genuinely complete.

    The original version called requests.get and wrote response.content with no
    status check at all. On a flaky connection that silently produced a
    truncated file, and on an HTTP error it wrote the error page itself into a
    .mp4, which then crashed the render. Either way the segment was lost and
    the finished video had a hole in it.

    This routes through the resilient downloader instead: transient failures
    are retried with exponential backoff and resumed with HTTP Range requests,
    the finished file is size-checked against Content-Length, and the
    container header is verified so an HTML error page is never accepted as
    video. There is no size limit; a large clip is downloaded in full.
    """
    from utility.core.resilient_download import download_with_retries

    result = download_with_retries(url, filename, kind=kind, max_attempts=8)
    if not result.ok:
        raise RuntimeError(
            f"Download did not complete after {result.attempts} attempts: "
            f"{result.reason}"
        )
    return filename

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    program_path = search_program(program_name)
    return program_path


def _fit_to_frame(clip, frame_width, frame_height):
    """Scale and centre-crop a clip so it fills the output frame exactly.

    Clips arrive at whatever resolution and aspect the source happened to hold.
    Compositing them untouched had two consequences: MoviePy took the finished
    video's size from the first clip in the list, so one 640x360 result shrank
    everything; and a landscape clip dropped into a portrait render left black
    bars down both sides.

    Scaling by the larger of the two ratios guarantees the frame is covered,
    then the overflow is cropped from the centre, which is where the subject of
    a stock clip almost always is.
    """
    if not clip.w or not clip.h:
        return clip
    if clip.w == frame_width and clip.h == frame_height:
        return clip

    scale = max(frame_width / clip.w, frame_height / clip.h)
    # Round up so rounding never leaves the frame one pixel short.
    new_width = max(frame_width, int(math.ceil(clip.w * scale)))
    new_height = max(frame_height, int(math.ceil(clip.h * scale)))
    resized = clip.resize(newsize=(new_width, new_height))

    x_centre = new_width / 2
    y_centre = new_height / 2
    return crop(resized, width=frame_width, height=frame_height,
                x_center=x_centre, y_center=y_centre)


def _stretch_to_slot(clip, slot_seconds):
    """Make a clip last at least as long as the slot it has to fill.

    set_end() cannot lengthen a clip. A source shorter than its slot therefore
    ran out mid-segment and the composite fell through to black while the
    narration kept talking -- the exact failure the footage stage works so hard
    to avoid. Looping fills the slot from the clip's own frames, and freezing
    the final frame is the fallback for a clip too short to loop cleanly.
    """
    if slot_seconds <= 0 or not clip.duration or clip.duration >= slot_seconds:
        return clip

    try:
        return loop(clip, duration=slot_seconds)
    except Exception:
        # Freeze the last frame for the remainder rather than show black.
        return clip.fx(freeze, t="end",
                       total_duration=slot_seconds, padding_end=0.05)

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server, background_music_path=None):
    config = get_config()
    
    # Check if rendering with Remotion is configured
    render_engine = os.getenv('RENDER_ENGINE', 'moviepy').lower()
    if render_engine == 'remotion':
        print("[RenderEngine] Routing compilation to React/Remotion renderer...")
        from utility.render.remotion_renderer import render_with_remotion
        return render_with_remotion(
            audio_file_path=audio_file_path,
            timed_captions=timed_captions,
            background_video_data=background_video_data,
            background_music_path=background_music_path
        )

    OUTPUT_FILE_NAME = "rendered_video.mp4"
    magick_path = get_program_path("magick") or get_program_path("convert")
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
        print(f"[RenderEngine] ImageMagick: {magick_path}")
    else:
        # Guessing /usr/bin/convert was wrong on ImageMagick 7, where the
        # legacy name is often absent. Say so instead, because captions are
        # the only thing affected and the render still produces a video.
        print("[RenderEngine] ImageMagick was not found on PATH. Captions "
              "cannot be drawn. Install it (Linux: 'imagemagick', macOS: "
              "'brew install imagemagick', Windows: imagemagick.org) or set "
              "IMAGEMAGICK_BINARY to its path.")

    # The output frame is decided by the configured orientation, not by
    # whichever clip happened to be downloaded first. Scraped sources return
    # whatever resolution they hold, so without this a single 640x360 clip in
    # first position used to shrink the entire video to 640x360.
    frame_width, frame_height = (1920, 1080) if config.get_video_orientation() \
        else (1080, 1920)
    print(f"[RenderEngine] Output frame: {frame_width}x{frame_height}.")

    visual_clips = []
    downloaded_files = []
    failures = []
    for (t1, t2), video_url in background_video_data:
        # Every clip must arrive complete. A segment rendered without its
        # footage becomes a black flash while the narration keeps talking, so
        # a failure here stops the render rather than producing a broken file.
        # The downloader has already retried, resumed and rotated through
        # dozens of user agents before it gives up.
        video_filename = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        try:
            download_file(video_url, video_filename)
            video_clip = VideoFileClip(video_filename)
            downloaded_files.append(video_filename)
        except Exception as error:
            failures.append((t1, t2, str(error)[:100]))
            continue

        try:
            video_clip = _fit_to_frame(video_clip, frame_width, frame_height)
            video_clip = _stretch_to_slot(video_clip, t2 - t1)
        except Exception as error:
            failures.append((t1, t2, f"could not be fitted to the frame: "
                                     f"{str(error)[:80]}"))
            continue

        video_clip = video_clip.set_start(t1)
        video_clip = video_clip.set_end(t2)
        visual_clips.append(video_clip)

    if failures:
        for path in downloaded_files:
            try:
                os.remove(path)
            except OSError:
                pass
        detail = "; ".join(f"{a:.1f}-{b:.1f}s ({why})" for a, b, why in failures[:3])
        raise RuntimeError(
            f"{len(failures)} of {len(background_video_data)} clips could not be "
            f"downloaded completely: {detail}"
            f"{' and more' if len(failures) > 3 else ''}.\n"
            f"The render was stopped rather than produce a video with black gaps "
            f"in it. The checkpoint is saved, so running the same topic again "
            f"resumes from this stage."
        )

    audio_clips = []
    audio_file_clip = AudioFileClip(audio_file_path)
    audio_clips.append(audio_file_clip)

    if background_music_path and os.path.exists(background_music_path):
        # Degraded path. In a normal run utility.audio.audio_mixer has already
        # folded the music into the narration with sidechain ducking, an EQ
        # carve around the speech band and -14 LUFS normalisation, and the
        # pipeline then passes background_music_path=None precisely so this
        # does not lay a second copy underneath. Reaching here means the mixer
        # failed, so this is a flat 12% bed: audible, but not mixed.
        print("[RenderEngine] The audio mixer did not run, so the music is "
              "being laid under the voice at a flat 12% with no ducking. "
              "The result is noticeably worse than a normal render.")
        try:
            bg_music_clip = AudioFileClip(background_music_path)
            bg_music_clip = bg_music_clip.volumex(0.12)
            # Loop bg music if it's shorter than voiceover
            if bg_music_clip.duration < audio_file_clip.duration:
                bg_music_clip = audio_loop(bg_music_clip, duration=audio_file_clip.duration)
            else:
                bg_music_clip = bg_music_clip.set_duration(audio_file_clip.duration)
            audio_clips.append(bg_music_clip)
        except Exception as e:
            print(f"[RenderEngine] Error loading/mixing background music: {e}")

    # Only add captions if enabled in config
    if config.get_captions_enabled():
        # A caption style preset decides the grouping, the look, the place in
        # the frame and the entrance. CAPTION_STYLE=auto picks the preset that
        # suits the script style. The individual CAPTION_* settings still work
        # and are applied on top of the preset.
        try:
            style = caption_style_from_env(config.get_video_style())
        except Exception as error:
            print(f"[RenderEngine] Could not read the video style: {error}")
            style = caption_style_from_env(None)

        print(f"[RenderEngine] Captions: style '{style['name']}', "
              f"frame {frame_width}x{frame_height}.")
        visual_clips.extend(
            build_caption_clips(timed_captions, style, frame_width, frame_height)
        )

    
    # A drifting handle watermark, if one is configured. Added after the
    # captions so it draws on top of the footage, and it steers around the
    # caption band so the text stays readable.
    watermark_duration = audio_file_clip.duration
    watermark_clip = build_watermark(frame_width, frame_height, watermark_duration)
    if watermark_clip is not None:
        visual_clips.append(watermark_clip)

    # Pass the size explicitly. Without it MoviePy takes the finished video's
    # dimensions from the first clip in the list, which is whatever the footage
    # search happened to return first.
    video = CompositeVideoClip(visual_clips, size=(frame_width, frame_height))

    if audio_clips:
        audio = CompositeAudioClip(audio_clips)
        video.duration = audio.duration
        video.audio = audio

    # 30 fps, matching the Remotion compositions, so the two renderers do not
    # produce visibly different output for the same settings. 25 was a PAL
    # broadcast rate and is not what any short-form platform expects.
    try:
        video.write_videofile(
            OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac',
            fps=OUTPUT_FPS, preset='veryfast',
            threads=os.cpu_count() or 2,
        )
    finally:
        # Release the ffmpeg reader each clip holds open. Without this a long
        # render keeps dozens of subprocesses and their buffers alive until the
        # interpreter exits, and on Windows the temp files below cannot be
        # deleted while they are still open.
        for clip in visual_clips:
            try:
                clip.close()
            except Exception:
                pass
        try:
            video.close()
        except Exception:
            pass
        for clip in audio_clips:
            try:
                clip.close()
            except Exception:
                pass

        # Clean up downloaded files.
        # The original loop called NamedTemporaryFile again here, which created
        # a brand new empty file and deleted that instead of the clip. Every
        # real download was left behind. The actual paths are tracked now.
        for path in downloaded_files:
            try:
                os.remove(path)
            except OSError:
                pass

    return OUTPUT_FILE_NAME
