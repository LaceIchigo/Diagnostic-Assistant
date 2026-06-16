"""
services/audio_service.py — Audio recording, VAD, and Whisper transcription.
Holds the shared session state dict and the recording thread.
"""
import os
import sys
import queue
import threading

import torch
import numpy as np
import sounddevice as sd

SAMPLE_RATE    = 16000
PAS_VERIFICARE = 0.5
MIN_CHUNK      = 2.0
MAX_CHUNK      = 8.0

print("Loading Whisper + Silero VAD...")
_stderr = sys.stderr
sys.stderr = open(os.devnull, "w")
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline          # imported here so stderr is suppressed
sys.stderr = _stderr

whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
vad_model, _utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad", model="silero_vad", trust_repo=True
)
get_speech_timestamps = _utils[0]
print("Models ready!")

# In-memory session store — shared across all routers
sesiuni_active: dict = {}


def recording_thread(session_id: str, transcript_queue: queue.Queue, stop_event: threading.Event):
    sesiune = sesiuni_active[session_id]
    audio_queue: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):  # noqa: ARG001
        audio_queue.put(indata.copy())

    buffer_curent = []
    timp_total = 0.0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=int(SAMPLE_RATE * PAS_VERIFICARE),
        channels=1,
        dtype="int16",
        callback=callback,
    ):
        print(f"[{session_id[:8]}] sounddevice stream open")
        while not stop_event.is_set():
            try:
                date_audio = audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            buffer_curent.append(date_audio)
            sesiune["istoric_audio_complet"].append(date_audio)

            chunk_flat = np.concatenate(buffer_curent, axis=0).flatten()
            durata = len(chunk_flat) / SAMPLE_RATE

            taiem_aici = False
            if durata >= MAX_CHUNK:
                taiem_aici = True
            elif durata >= MIN_CHUNK:
                ultima_sec_float = chunk_flat[-SAMPLE_RATE:].astype(np.float32) / 32768.0
                voices = get_speech_timestamps(
                    torch.from_numpy(ultima_sec_float), vad_model, sampling_rate=SAMPLE_RATE
                )
                if not voices:
                    taiem_aici = True

            if taiem_aici:
                chunk_float32 = chunk_flat.astype(np.float32) / 32768.0
                segments, _ = whisper_model.transcribe(
                    chunk_float32, beam_size=5, language="en", vad_filter=True
                )
                for seg in segments:
                    text = seg.text.strip()
                    if text:
                        start_real = timp_total + seg.start
                        end_real   = timp_total + seg.end
                        print(f"   [{start_real:.1f}s] {text}")
                        sesiune["transcript_brut"].append(
                            {"start": start_real, "end": end_real, "text": text}
                        )
                        transcript_queue.put(text)

                timp_total += durata
                sesiune["timp_total_inregistrat"] = timp_total
                buffer_curent = []

    print(f"[{session_id[:8]}] thread done — {timp_total:.1f}s recorded")
