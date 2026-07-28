import os
import asyncio
import imageio_ffmpeg

# Automatically register imageio-ffmpeg binary as ffmpeg.exe in the PATH for Whisper and other subprocesses
ffmpeg_exe_src = imageio_ffmpeg.get_ffmpeg_exe()
bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
os.makedirs(bin_dir, exist_ok=True)
ffmpeg_exe_dest = os.path.join(bin_dir, "ffmpeg.exe")

if not os.path.exists(ffmpeg_exe_dest):
    print(f"[Pipeline] Copying bundled ffmpeg to local bin: {ffmpeg_exe_src} -> {ffmpeg_exe_dest}")
    import shutil
    shutil.copy2(ffmpeg_exe_src, ffmpeg_exe_dest)

if bin_dir not in os.environ["PATH"]:
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed
from utility.media.media_manager import MediaSourceManager, merge_empty_intervals
from utility.audio.key_moment_detector import KeyMomentDetector
from utility.audio.audio_mixer import AudioMixer
from utility.publishing.metadata_generator import MetadataGenerator, to_text
from utility.core.naming import output_stem, unique_path
from utility.ui import gallery_manager
from utility.config import get_config
from utility.pipeline_manager import PipelineManager

def download_file(url, filename, kind="audio"):
    """Download a file, retrying and resuming until it is genuinely complete.

    Uses the same resilient downloader as the clips, so a music track is not
    lost to one bad moment on the connection.
    """
    print(f"[Pipeline] Downloading: {url} -> {filename}")
    from utility.core.resilient_download import download_with_retries

    result = download_with_retries(url, filename, kind=kind, max_attempts=8)
    if not result.ok:
        raise RuntimeError(
            f"Download did not complete after {result.attempts} attempts: "
            f"{result.reason}"
        )
    return filename

def run(topic_argument: str) -> None:
    """Generate one video, start to finish.

    Seven stages, each checkpointed. An interrupted run resumes from where it
    stopped; a different topic starts fresh.

    This is called in a subprocess by the interface rather than imported, so a
    long render cannot block the browser and so a crash cannot take the
    interface down with it.
    """
    config = get_config()
    orientation_landscape = config.get_video_orientation()
    aspect_ratio = "16:9" if orientation_landscape else "9:16"

    # Initialize PipelineManager
    manager = PipelineManager(topic_argument)
    topic = manager.get_data("topic")

    # Every clip, image, music track and sound effect comes from free,
    # zero-attribution sources. Paid AI video and music generators are
    # deliberately absent: this project does not use paid services.
    media = MediaSourceManager()
    style_name = config.get_video_style()

    # 1. Generate Script
    if manager.get_stage() == "1_script":
        print("\n--- STAGE 1: Generating Script ---")
        script = generate_script(topic)
        print(f"Generated Script: {script}")
        manager.update_data("script", script)
        manager.set_stage("2_voiceover")

    # 2. Generate Voiceover
    if manager.get_stage() == "2_voiceover":
        print("\n--- STAGE 2: Generating Voiceover ---")
        script = manager.get_data("script")
        voiceover_filename = "audio_tts.wav"
        # The style and topic let the voice be chosen to suit the script, and
        # keep that choice stable if this stage is resumed after a failure.
        voice_used = asyncio.run(generate_audio(
            script, voiceover_filename,
            style=config.get_video_style(), topic=topic,
        ))
        manager.update_data("voice_used", voice_used)
        print(f"Generated voiceover saved to: {voiceover_filename}")
        manager.update_data("voiceover_path", voiceover_filename)
        manager.set_stage("3_timed_captions")

    # 3. Generate Timed Captions
    if manager.get_stage() == "3_timed_captions":
        print("\n--- STAGE 3: Generating Timed Captions ---")
        voiceover_filename = manager.get_data("voiceover_path")
        timed_captions = generate_timed_captions(voiceover_filename)
        print(f"Generated timed captions: {timed_captions}")
        manager.update_data("timed_captions", timed_captions)
        manager.set_stage("4_background_music")

    # 4. Background Music and Sound Effects
    if manager.get_stage() == "4_background_music":
        print("\n--- STAGE 4: Background Music and Sound Effects ---")
        script = manager.get_data("script")
        timed_captions = manager.get_data("timed_captions")

        # Music is chosen from the mood the script style implies, so a true
        # crime piece gets tension and a travel piece gets something uplifting.
        music_url = media.find_music(style_name, topic)
        if music_url:
            local_music_path = "background_music.mp3"
            try:
                download_file(music_url, local_music_path)
                manager.update_data("background_music_url", music_url)
                manager.update_data("background_music_path", local_music_path)
                print(f"Background music saved to: {local_music_path}")
            except Exception as e:
                print(f"Could not download the music track: {e}. Continuing without music.")
        else:
            print("No free music track matched this style. Continuing without music.")

        # Sound effects are placed where the narration earns them, not
        # sprinkled at random: reveals, hard transitions, questions and
        # action words. The density cap keeps them from becoming noise.
        if config.get_sfx_enabled():
            detector = KeyMomentDetector(config.get_sfx_density())
            moments = detector.detect(script, timed_captions)
            placed = []
            for moment in moments:
                sfx_url = media.find_sfx(moment["sfx_query"])
                if not sfx_url:
                    continue
                path = media.download_to_temp(sfx_url, suffix=".mp3", kind="audio")
                if path:
                    placed.append({"path": path, "time": moment["time"],
                                   "query": moment["sfx_query"]})
            manager.update_data("sfx_items", placed)
            print(f"Placed {len(placed)} sound effects from {len(moments)} key moments.")
        else:
            manager.update_data("sfx_items", [])
            print("Sound effects are switched off.")

        manager.set_stage("5_ai_video_broll")

    # 5. Source Timed B-roll Footage
    if manager.get_stage() == "5_ai_video_broll":
        print("\n--- STAGE 5: Sourcing Timed B-Roll Footage ---")
        script = manager.get_data("script")
        timed_captions = manager.get_data("timed_captions")
        search_terms = getVideoSearchQueriesTimed(script, timed_captions)

        # One clip per timed segment, searched across every free source in
        # priority order. The segment's own keywords are tried first so each
        # shot matches the sentence being spoken.
        background_video_urls = media.generate_video_url(
            search_terms,
            orientation_landscape=orientation_landscape,
            style_name=style_name,
            topic=topic,
        )
        # Nothing is allowed through without footage. A missing segment is not
        # a cosmetic problem: the renderer composites onto black, so the
        # finished video carries a black flash exactly where the narration is
        # still talking. Stopping here is the right outcome, because the
        # checkpoint is saved and re-running resumes from this stage once the
        # connection is back.
        gaps = [(t1, t2) for (t1, t2), url in background_video_urls if not url]
        if gaps:
            raise RuntimeError(
                f"{len(gaps)} of {len(background_video_urls)} segments could not "
                f"be filled after trying every free source: "
                f"{', '.join(f'{a:.1f}-{b:.1f}s' for a, b in gaps[:5])}"
                f"{' and more' if len(gaps) > 5 else ''}.\n"
                f"Nothing has been lost. The checkpoint is saved, so running the "
                f"same topic again resumes from this stage. Check the connection "
                f"first, and add a free Pixabay key in Settings if you have not, "
                f"since it widens the search considerably."
            )

        manager.update_data("background_video_urls", background_video_urls)
        if media.credits_line():
            print(media.credits_line())
        print(f"All {len(background_video_urls)} segments have footage.")

        manager.set_stage("6_render")

    # 6. Render final composite video
    if manager.get_stage() == "6_render":
        print("\n--- STAGE 6: Rendering Final Video ---")
        voiceover_path = manager.get_data("voiceover_path")
        timed_captions = manager.get_data("timed_captions")
        background_video_urls = manager.get_data("background_video_urls")
        background_music_path = manager.get_data("background_music_path")
        sfx_items = manager.get_data("sfx_items") or []

        # Mix the voice, the music and the sound effects into one track before
        # rendering. This is what makes them sit together: the music is ducked
        # under the voice by a sidechain compressor, the 800 Hz and 2 kHz range
        # is carved out of the music so speech stays intelligible, and the whole
        # mix is normalised to -14 LUFS, the level the platforms expect.
        # Handing three separate tracks to MoviePy instead would just sum them.
        if background_music_path or sfx_items:
            try:
                mixer = AudioMixer()
                mixed = mixer.mix(voiceover_path,
                                  music_path=background_music_path,
                                  sfx_items=sfx_items)
                report = mixer.mix_report()
                print(f"[Pipeline] Audio mixed: music at {report['music_idle_db']} dB "
                      f"ducking to {report['music_ducked_db']} dB, "
                      f"{len(sfx_items)} effects, normalised to "
                      f"{report['target_lufs']} LUFS.")
                voiceover_path = mixed
                # The music is already inside the mix; passing it on as well
                # would lay a second, unducked copy under the video.
                background_music_path = None
            except Exception as e:
                print(f"[Pipeline] Audio mix failed: {e}. Using the plain voiceover.")

        # Clean/merge intervals
        background_video_urls = merge_empty_intervals(background_video_urls)

        if background_video_urls:
            print("Compiling media files...")
            video_output = get_output_media(
                audio_file_path=voiceover_path,
                timed_captions=timed_captions,
                background_video_data=background_video_urls,
                video_server="pexel", # Just standard downloader
                background_music_path=background_music_path
            )
            print(f"\nSUCCESS! Final video saved as '{video_output}'")
            manager.update_data("video_path", video_output)
            manager.set_stage("7_metadata")
        else:
            print("Error: No background video clips found. Cannot render.")

    # 7. Write the upload packages
    if manager.get_stage() == "7_metadata":
        print("\n--- STAGE 7: Writing Upload Packages ---")
        script = manager.get_data("script")
        timed_captions = manager.get_data("timed_captions") or []
        duration = timed_captions[-1][0][1] if timed_captions else 0.0

        # A rendered file with no title, description or hashtags cannot be
        # published. This writes all three platform packages in one model call,
        # then measures the result against the platforms' real limits rather
        # than trusting what came back.
        try:
            packages = MetadataGenerator(config).generate(
                topic=topic, script=script, style_name=style_name,
                duration_seconds=duration,
            )
            manager.update_data("metadata", packages)

            # Name the rendered file after the title it will be uploaded
            # under, with a hyphen between every word. "rendered_video.mp4"
            # tells you nothing once a few videos are sitting in the folder.
            video_path = manager.get_data("video_path")
            if video_path and os.path.exists(video_path):
                # Finished videos live in outputs/ under the title they will
                # be uploaded with, so the gallery can list them and the
                # project root stays clean.
                folder = gallery_manager.outputs_dir()
                stem = output_stem(packages["youtube"]["title"], topic)
                extension = os.path.splitext(video_path)[1] or ".mp4"
                target = unique_path(folder, stem, extension)
                try:
                    os.replace(video_path, target)
                    manager.update_data("video_path", target)
                    print(f"Saved video    : outputs/{os.path.basename(target)}")

                    packages_name = os.path.splitext(
                        os.path.basename(target))[0] + ".txt"
                    packages_path = os.path.join(folder, packages_name)
                    with open(packages_path, "w", encoding="utf-8") as handle:
                        handle.write(to_text(packages))
                    manager.update_data("metadata_path", packages_path)

                    gallery_manager.record(
                        filename=target, topic=topic,
                        title=packages["youtube"]["title"], style=style_name,
                        duration=duration,
                        orientation="landscape" if orientation_landscape
                        else "portrait",
                        packages_file=packages_path,
                        voice=manager.get_data("voice_used") or "",
                    )
                except OSError as e:
                    print(f"Could not move the video ({e}); "
                          f"it stays as {video_path}.")

            report = packages["report"]
            print(f"YouTube title  : {packages['youtube']['title']}")
            print(f"Instagram tags : {report['instagram_hashtag_count']} "
                  f"(cap is 5)")
            print(f"TikTok tags    : {report['tiktok_hashtag_count']}")
            print(f"Thumbnail text : {packages['youtube']['thumbnail_text']}")
            if report["corrections_applied"]:
                print(f"{len(report['corrections_applied'])} platform limits "
                      f"were exceeded by the model and have been corrected.")
            print(f"Packages       : {manager.get_data('metadata_path') or 'not written'}")
        except Exception as e:
            print(f"Could not write the upload packages: {e}")

        manager.set_stage("completed")

    if manager.get_stage() == "completed":
        print("\nPipeline execution complete! Resetting checkpoint...")
        # Reset checkpoint for future runs
        if os.path.exists("pipeline_checkpoint.json"):
            try:
                os.remove("pipeline_checkpoint.json")
            except Exception as e:
                print(f"Error cleaning up checkpoint: {e}")
