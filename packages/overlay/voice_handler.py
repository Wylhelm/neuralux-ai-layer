"""Voice capture and processing for overlay."""

import threading
import tempfile
import struct
from typing import Callable, Optional
from gi.repository import GLib
import structlog

logger = structlog.get_logger(__name__)


class VoiceHandler:
    """Handles voice capture and STT processing for overlay."""

    def __init__(self, config, message_bus=None):
        """Initialize voice handler.

        Args:
            config: Overlay config with VAD settings
            message_bus: Optional message bus for STT requests
        """
        self.config = config
        self._message_bus = message_bus
        self._tts_lock = threading.Lock()

    def capture_voice(
        self,
        on_transcript: Callable[[str], None],
        on_error: Callable[[str], None],
        on_recording_state: Callable[[bool], None],
        short_mode: bool = False,
    ):
        """Capture voice with VAD detection and run STT.

        Args:
            on_transcript: Called with transcript text when ready
            on_error: Called with error message on failure
            on_recording_state: Called with True/False to indicate recording state
            short_mode: If True, use shorter timings for approval flows
        """
        # Signal recording start
        try:
            on_recording_state(True)
        except Exception:
            pass

        def _worker():
            try:
                # Check if audio service is available
                if not self._message_bus:
                    GLib.idle_add(
                        lambda: (
                            on_recording_state(False),
                            on_error("Message bus not connected"),
                        )
                        or False
                    )
                    return

                # Capture audio with VAD
                temp_path = self._capture_audio_with_vad(short_mode)

                if not temp_path:
                    GLib.idle_add(
                        lambda: (
                            on_recording_state(False),
                            on_error("No speech detected"),
                        )
                        or False
                    )
                    return

                # Run STT
                transcript = self._run_stt(temp_path)

                # Clean up temp file
                try:
                    import os

                    os.unlink(temp_path)
                except Exception:
                    pass

                # Signal recording end
                GLib.idle_add(lambda: on_recording_state(False) or False)

                if not transcript:
                    GLib.idle_add(lambda: on_error("Didn't catch that") or False)
                    logger.warning("Voice capture: no transcript")
                    return

                # Return transcript
                logger.info(
                    "Voice capture: transcript received", length=len(transcript)
                )
                GLib.idle_add(lambda: on_transcript(transcript) or False)

            except Exception as e:
                logger.error("Voice capture error", error=str(e), exc_info=True)
                GLib.idle_add(
                    lambda: (on_recording_state(False), on_error(f"Voice error: {e}"))
                    or False
                )

        threading.Thread(target=_worker, daemon=True).start()

    def _capture_audio_with_vad(self, short_mode: bool = False) -> Optional[str]:
        """Capture audio with VAD and return path to WAV file.

        Args:
            short_mode: If True, use shorter timings

        Returns:
            Path to temporary WAV file, or None if no speech detected
        """
        try:
            import pyaudio
            import wave

            audio_format = pyaudio.paInt16
            channels = 1
            rate = 16000
            chunk = 1024

            p = pyaudio.PyAudio()
            stream = p.open(
                format=audio_format,
                channels=channels,
                rate=rate,
                input=True,
                frames_per_buffer=chunk,
            )
            frames = []

            # Get VAD parameters
            if short_mode:
                # Shorter timings for approval flows
                cfg_threshold = float(
                    getattr(self.config, "vad_silence_threshold", 0.01)
                )
                silence_duration = 0.5
                max_recording_time = 6
                min_recording_time = 0.6
                calibration_time = 0.3
            else:
                # Normal conversational timings
                cfg_threshold = float(
                    getattr(self.config, "vad_silence_threshold", 0.01)
                )
                silence_duration = float(
                    getattr(self.config, "vad_silence_duration", 1.5)
                )
                max_recording_time = int(
                    getattr(self.config, "vad_max_recording_time", 15)
                )
                min_recording_time = int(
                    getattr(self.config, "vad_min_recording_time", 1)
                )
                calibration_time = 0.4

            silence_frames = 0
            silence_frame_count = int(rate / chunk * silence_duration)
            total_frames = 0
            max_frames = int(rate / chunk * max_recording_time)
            min_frames = int(rate / chunk * min_recording_time)
            speech_detected = False

            # Dynamic noise calibration
            try:
                calibration_frames = max(1, int(rate / chunk * calibration_time))
                noise_accum = 0.0
                noise_count = 0

                for _ in range(calibration_frames):
                    data0 = stream.read(chunk, exception_on_overflow=False)
                    frames.append(data0)
                    total_frames += 1
                    audio_cal = struct.unpack(f"{chunk}h", data0)
                    rms0 = (sum(x * x for x in audio_cal) / len(audio_cal)) ** 0.5
                    noise_accum += rms0
                    noise_count += 1

                noise_rms = (noise_accum / max(1, noise_count)) if noise_count else 0.0
                dyn_factor = float(getattr(self.config, "vad_dynamic_factor", 1.8))
                min_rms = int(getattr(self.config, "vad_min_rms", 120))
                silence_threshold = (
                    max(int(noise_rms * dyn_factor), min_rms)
                    if cfg_threshold < 1.0
                    else cfg_threshold
                )
            except Exception:
                silence_threshold = int(getattr(self.config, "vad_min_rms", 120))

            # Record with VAD
            while total_frames < max_frames:
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)
                total_frames += 1

                audio_data = struct.unpack(f"{chunk}h", data)
                rms = (sum(x * x for x in audio_data) / len(audio_data)) ** 0.5

                if rms > silence_threshold:
                    speech_detected = True
                    silence_frames = 0
                else:
                    silence_frames += 1
                    if (
                        silence_frames >= silence_frame_count
                        and total_frames >= min_frames
                        and speech_detected
                    ):
                        break

            stream.stop_stream()
            stream.close()

            if not speech_detected:
                p.terminate()
                return None

            # Get sample size BEFORE terminating PyAudio
            sample_width = p.get_sample_size(audio_format)
            p.terminate()

            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            wf = wave.open(temp_path, "wb")
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(b"".join(frames))
            wf.close()

            return temp_path

        except Exception as e:
            logger.error("Audio capture error", error=str(e))
            return None

    def _run_stt(self, audio_path: str) -> str:
        """Run STT on audio file.

        Args:
            audio_path: Path to WAV file

        Returns:
            Transcript text (may be empty)
        """
        try:
            import httpx

            language = getattr(self.config, "stt_language", "en")
            transcript = ""

            # First: try with VAD filter
            try:
                with open(audio_path, "rb") as f:
                    files = {"file": ("speech.wav", f, "audio/wav")}
                    resp = httpx.post(
                        "http://localhost:8006/stt/file",
                        params={"language": language, "vad_filter": "true"},
                        files=files,
                        timeout=60.0,
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    transcript = (data.get("text") or "").strip()
            except Exception:
                pass

            # Second: retry without VAD if empty
            if not transcript:
                try:
                    with open(audio_path, "rb") as f:
                        files = {"file": ("speech.wav", f, "audio/wav")}
                        resp = httpx.post(
                            "http://localhost:8006/stt/file",
                            params={"language": language, "vad_filter": "false"},
                            files=files,
                            timeout=60.0,
                        )
                    if resp.status_code == 200:
                        data = resp.json()
                        transcript = (data.get("text") or "").strip()
                except Exception:
                    pass

            # Third: fallback to message bus STT if still empty
            if not transcript and self._message_bus:
                try:
                    stt_fb = self._message_bus.request(
                        "ai.audio.stt",
                        {
                            "audio_path": audio_path,
                            "vad_filter": False,
                            "language": language,
                        },
                        timeout=30.0,
                    )
                    try:
                        stt_fb = (
                            stt_fb if isinstance(stt_fb, dict) else stt_fb.result(30.0)
                        )
                    except Exception:
                        pass
                    if isinstance(stt_fb, dict) and "error" not in stt_fb:
                        transcript = (stt_fb.get("text") or "").strip()
                except Exception:
                    pass

            return transcript

        except Exception as e:
            logger.error("STT error", error=str(e))
            return ""

    def speak(self, text: str):
        """Speak text using TTS (async, best-effort).

        Args:
            text: Text to speak (will be truncated to 220 chars)
        """
        if not text:
            return

        def _worker():
            import base64
            import tempfile
            import subprocess
            import os
            import shutil
            import httpx

            try:
                # Serialize playback to avoid driver/sink contention
                acquired = False
                if self._tts_lock is not None:
                    acquired = self._tts_lock.acquire(blocking=False)
                    if not acquired:
                        logger.warning("TTS playback skipped: busy")
                        return

                try:
                    # Request TTS audio from audio service
                    resp = httpx.post(
                        "http://localhost:8006/tts",
                        json={"text": text[:220], "output_format": "wav"},
                        timeout=30.0,
                    )
                    if resp.status_code != 200:
                        logger.error("TTS HTTP error", status=resp.status_code)
                        return

                    data = resp.json()
                    audio_b64 = data.get("audio_data", "")
                    if not audio_b64:
                        logger.error("TTS response missing audio_data")
                        return

                    audio_data = base64.b64decode(audio_b64)
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(audio_data)
                        path = f.name

                    try:
                        # Try paplay, then aplay, then ffplay
                        played = False

                        try:
                            subprocess.run(
                                ["paplay", path],
                                check=True,
                                capture_output=True,
                                timeout=20,
                            )
                            played = True
                        except subprocess.TimeoutExpired:
                            logger.error("TTS playback timed out", player="paplay")
                        except Exception as e:
                            logger.warning("paplay failed; falling back", error=str(e))

                        if not played:
                            try:
                                subprocess.run(
                                    ["aplay", path],
                                    check=True,
                                    capture_output=True,
                                    timeout=20,
                                )
                                played = True
                            except subprocess.TimeoutExpired:
                                logger.error("TTS playback timed out", player="aplay")
                            except Exception as e:
                                logger.warning(
                                    "aplay failed; falling back", error=str(e)
                                )

                        if not played and shutil.which("ffplay"):
                            try:
                                subprocess.run(
                                    [
                                        "ffplay",
                                        "-nodisp",
                                        "-autoexit",
                                        "-loglevel",
                                        "error",
                                        path,
                                    ],
                                    check=True,
                                    capture_output=True,
                                    timeout=25,
                                )
                                played = True
                            except subprocess.TimeoutExpired:
                                logger.error("TTS playback timed out", player="ffplay")
                            except Exception as e:
                                logger.error("ffplay failed", error=str(e))

                        if not played:
                            logger.error("No audio player succeeded for TTS")
                    finally:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass
                finally:
                    if self._tts_lock is not None and acquired:
                        try:
                            self._tts_lock.release()
                        except Exception:
                            pass
            except Exception as e:
                logger.error("TTS playback error", error=str(e))

        threading.Thread(target=_worker, daemon=True).start()
