from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid, os, sys, time, asyncio, threading
import torch
import numpy as np
import queue
import sounddevice as sd

from modul_llm import genereaza_raport_medical

stderr_original = sys.stderr
sys.stderr = open(os.devnull, 'w')
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
sys.stderr = stderr_original

TOKEN_HUGGINGFACE = "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"
SAMPLE_RATE    = 16000
PAS_VERIFICARE = 0.5   # same as app_cabinet.py
MIN_CHUNK      = 2.0
MAX_CHUNK      = 8.0

print("⏳ Loading Whisper + Silero VAD (same as app_cabinet.py)...")
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
vad_model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True
)
get_speech_timestamps = utils[0]
print("✅ Models ready!")

app = FastAPI(title="Medical AI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

sesiuni_active = {}


# ─────────────────────────────────────────────────────────────────────────────
# Recording thread — copy of app_cabinet.py logic, adapted for a thread
# ─────────────────────────────────────────────────────────────────────────────

def recording_thread(session_id: str, transcript_queue: queue.Queue, stop_event: threading.Event):
    sesiune = sesiuni_active[session_id]
    audio_queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        audio_queue.put(indata.copy())

    buffer_curent = []
    timp_total = 0.0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=int(SAMPLE_RATE * PAS_VERIFICARE),
        channels=1,
        dtype='int16',
        callback=callback,
    ):
        print(f"🎙️  [{session_id[:8]}] sounddevice stream open")
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
                ultima_sec = chunk_flat[-SAMPLE_RATE:]
                ultima_sec_float = ultima_sec.astype(np.float32) / 32768.0
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
                        print(f"   ✏️  [{start_real:.1f}s] {text}")
                        sesiune["transcript_brut"].append({
                            "start": start_real, "end": end_real, "text": text
                        })
                        transcript_queue.put(text)

                timp_total += durata
                sesiune["timp_total_inregistrat"] = timp_total
                buffer_curent = []

    print(f"🛑 [{session_id[:8]}] thread done — {timp_total:.1f}s recorded")


# ─────────────────────────────────────────────────────────────────────────────
# API endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/sessions")
async def creare_sesiune():
    session_id = str(uuid.uuid4())
    sesiuni_active[session_id] = {
        "status": "created",
        "istoric_audio_complet": [],
        "transcript_brut": [],
        "timp_total_inregistrat": 0.0,
        "rezultat_final": None,
        "stop_event": None,
        "thread": None,
    }
    print(f"✅ Session: {session_id[:8]}")
    return {"session_id": session_id, "status": "created"}


@app.websocket("/sessions/{session_id}/stream")
async def websocket_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    if session_id not in sesiuni_active:
        await websocket.close()
        return

    sesiune = sesiuni_active[session_id]
    sesiune["status"] = "streaming"

    transcript_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    sesiune["stop_event"] = stop_event

    # Start sounddevice recording thread (same pipeline as app_cabinet.py)
    thread = threading.Thread(
        target=recording_thread,
        args=(session_id, transcript_queue, stop_event),
        daemon=True,
    )
    sesiune["thread"] = thread
    thread.start()
    print(f"🟢 [{session_id[:8]}] Recording started")

    try:
        while True:
            # Forward any new transcript lines to the browser
            while not transcript_queue.empty():
                text = transcript_queue.get_nowait()
                await websocket.send_json({"type": "partial_transcript", "text": text})

            # Wait briefly; also catches disconnect
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

            await asyncio.sleep(0.1)

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        stop_event.set()
        print(f"🔴 [{session_id[:8]}] WebSocket closed")


@app.post("/sessions/{session_id}/stop")
async def oprire_sesiune(session_id: str):
    if session_id not in sesiuni_active:
        raise HTTPException(status_code=404, detail="Invalid session")

    sesiune = sesiuni_active[session_id]

    # Stop the recording thread
    if sesiune["stop_event"]:
        sesiune["stop_event"].set()
    if sesiune["thread"] and sesiune["thread"].is_alive():
        sesiune["thread"].join(timeout=5)

    sesiune["status"] = "processing"
    print("\n" + "="*54)
    print("🛑  Post-processing: diarization + LLM")
    print(f"    Segments collected: {len(sesiune['transcript_brut'])}")
    print("="*54)

    if not sesiune["istoric_audio_complet"]:
        sesiune["status"] = "completed"
        sesiune["rezultat_final"] = {
            "summary": "No audio was recorded.",
            "suggestions": [], "disclaimer": ""
        }
        return {"message": "No audio", "status": "completed"}

    # ── Diarization (identical to app_cabinet.py) ────────────────────────
    audio_flat  = np.concatenate(sesiune["istoric_audio_complet"], axis=0).flatten()
    audio_float = audio_flat.astype(np.float32) / 32768.0

    print("⏳ Loading Pyannote...")
    pyannote_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", token=TOKEN_HUGGINGFACE
    )
    print("🔍 Diarizing...")
    waveform = torch.from_numpy(audio_float).unsqueeze(0)
    t0 = time.time()
    diarizare = pyannote_pipeline(
        {"waveform": waveform, "sample_rate": SAMPLE_RATE}, num_speakers=2
    )
    print(f"⏱️  Diarization: {time.time()-t0:.1f}s")

    if hasattr(diarizare, "speaker_diarization"):
        diarizare = diarizare.speaker_diarization

    # ── Match transcript to speakers (identical to app_cabinet.py) ───────
    transcript_llm = ""
    for item in sesiune["transcript_brut"]:
        best_overlap, speaker = 0, "UNKNOWN"
        for turn, _, spk in diarizare.itertracks(yield_label=True):
            overlap = min(item["end"], turn.end) - max(item["start"], turn.start)
            if overlap > best_overlap:
                best_overlap, speaker = overlap, spk
        transcript_llm += f"{speaker}: {item['text']}\n"

    print("\n📄 Transcript:\n" + transcript_llm)
    print("🧠 Calling LLM...")
    raport_text, timp = genereaza_raport_medical(transcript_llm)

    sesiune["rezultat_final"] = {
        "summary": raport_text,
        "suggestions": [],
        "disclaimer": f"LLM: {timp:.1f}s",
    }
    sesiune["status"] = "completed"
    print("✅ Done.")
    return {"message": "Done", "status": "completed"}


@app.get("/sessions/{session_id}/result")
async def preluare_rezultat(session_id: str):
    sesiune = sesiuni_active.get(session_id)
    if not sesiune:
        raise HTTPException(status_code=404, detail="Invalid session")
    if sesiune["status"] != "completed":
        return {"status": sesiune["status"], "message": "Still processing"}
    return {"status": "completed", "data": sesiune["rezultat_final"]}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Medical AI API — port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)