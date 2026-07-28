import time
import os
import tempfile
import zipfile
import platform
import subprocess
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip, ImageClip,
                              VideoFileClip)
from utility.render.caption_renderer import (build_caption_clips,
                                             caption_style_from_env,
                                             frame_size_from)
from utility.render.watermark import build as build_watermark
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_normalize import audio_normalize
from utility.config import get_config

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
    magick_path = get_program_path("magick")
    print(magick_path)
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'
    
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
        try:
            bg_music_clip = AudioFileClip(background_music_path)
            # Set volume of background music to 12% so voiceover remains clear
            bg_music_clip = bg_music_clip.volumex(0.12)
            # Loop bg music if it's shorter than voiceover
            if bg_music_clip.duration < audio_file_clip.duration:
                bg_music_clip = audio_loop(bg_music_clip, duration=audio_file_clip.duration)
            else:
                bg_music_clip = bg_music_clip.set_duration(audio_file_clip.duration)
            audio_clips.append(bg_music_clip)
            print("[RenderEngine] Successfully loaded and mixed background music.")
        except Exception as e:
            print(f"[RenderEngine] Error loading/mixing background music: {e}")

    
    # The frame the overlays have to fit. Worked out once, because both the
    # captions and the watermark need it.
    frame_width, frame_height = frame_size_from(
        visual_clips, config.get_video_orientation()
    )

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

    video = CompositeVideoClip(visual_clips)
    
    if audio_clips:
        audio = CompositeAudioClip(audio_clips)
        video.duration = audio.duration
        video.audio = audio

    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')
    
    # Clean up downloaded files.
    # The original loop called NamedTemporaryFile again here, which created a
    # brand new empty file and deleted that instead of the clip. Every real
    # download was left behind. The actual paths are tracked now.
    for path in downloaded_files:
        try:
            os.remove(path)
        except OSError:
            pass

    return OUTPUT_FILE_NAME
