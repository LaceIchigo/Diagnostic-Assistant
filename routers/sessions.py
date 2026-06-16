import asyncio
import queue
import threading
import time
import uuid

import numpy as np
import torch
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from models.database import get_db, Consultatie
from services.audio_service import (
    Pipeline,
    SAMPLE_RATE,
    recording_thread,
    sesiuni_active,
)
from services.gdpr_service import gdpr
from services.llm_service import genereaza_raport_medical

import os
TOKEN_HUGGINGFACE = os.getenv("HUGGINGFACE_TOKEN")

router = APIRouter(tags=["Sessions"])


@router.post("/sessions")
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
    print(f"Session: {session_id[:8]}")
    return {"session_id": session_id, "status": "created"}


@router.websocket("/sessions/{session_id}/stream")
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

    thread = threading.Thread(
        target=recording_thread,
        args=(session_id, transcript_queue, stop_event),
        daemon=True,
    )
    sesiune["thread"] = thread
    thread.start()
    print(f"[{session_id[:8]}] Recording started")

    try:
        while True:
            while not transcript_queue.empty():
                text = transcript_queue.get_nowait()
                await websocket.send_json({"type": "partial_transcript", "text": text})
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        stop_event.set()
        print(f"[{session_id[:8]}] WebSocket closed")


@router.post("/sessions/{session_id}/stop")
async def oprire_sesiune(session_id: str, pacient_id: int = None, db: Session = Depends(get_db)):
    if session_id not in sesiuni_active:
        raise HTTPException(status_code=404, detail="Invalid session")

    sesiune = sesiuni_active[session_id]

    if sesiune["stop_event"]:
        sesiune["stop_event"].set()
    if sesiune["thread"] and sesiune["thread"].is_alive():
        sesiune["thread"].join(timeout=5)

    sesiune["status"] = "processing"
    print("\n" + "=" * 54)
    print("Post-processing: diarization + LLM")
    print(f"    Segments collected: {len(sesiune['transcript_brut'])}")
    print("=" * 54)

    if not sesiune["istoric_audio_complet"]:
        sesiune["status"] = "completed"
        sesiune["rezultat_final"] = {
            "consultatie_id": None,
            "summary": "No audio was recorded.",
            "suggestions": [],
            "disclaimer": "",
        }
        return {"message": "No audio", "status": "completed"}

    audio_flat  = np.concatenate(sesiune["istoric_audio_complet"], axis=0).flatten()
    audio_float = audio_flat.astype(np.float32) / 32768.0

    print("Loading Pyannote...")
    pyannote_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", token=TOKEN_HUGGINGFACE
    )
    print("Diarizing...")
    waveform = torch.from_numpy(audio_float).unsqueeze(0)
    t0 = time.time()
    diarizare = pyannote_pipeline(
        {"waveform": waveform, "sample_rate": SAMPLE_RATE}, num_speakers=2
    )
    print(f"Diarization: {time.time() - t0:.1f}s")

    if hasattr(diarizare, "speaker_diarization"):
        diarizare = diarizare.speaker_diarization

    transcript_llm = ""
    for item in sesiune["transcript_brut"]:
        best_overlap, speaker = 0, "UNKNOWN"
        for turn, _, spk in diarizare.itertracks(yield_label=True):
            overlap = min(item["end"], turn.end) - max(item["start"], turn.start)
            if overlap > best_overlap:
                best_overlap, speaker = overlap, spk
        transcript_llm += f"{speaker}: {item['text']}\n"

    print("\nTranscript:\n" + transcript_llm)
    print("Calling LLM...")
    raport_text, timp = genereaza_raport_medical(transcript_llm)

    noua_consultatie = Consultatie(
        pacient_id=pacient_id,
        transcript_audio=gdpr.encrypt(transcript_llm),
        rezumat_diagnostic=gdpr.encrypt(raport_text),
        sugestii_tratament="Salvat automat din fluxul AI.",
    )
    db.add(noua_consultatie)
    db.commit()
    db.refresh(noua_consultatie)
    gdpr.log_access("CONSULTATION_SAVED", "medic", f"Consultatie ID {noua_consultatie.id}")
    print("Date salvate (criptate) in SQLite!")

    sesiune["rezultat_final"] = {
        "consultatie_id": noua_consultatie.id,
        "summary": raport_text,
        "suggestions": ["Date salvate in DB."],
        "disclaimer": f"LLM: {timp:.1f}s",
    }
    sesiune["status"] = "completed"
    print("Done.")
    return {"message": "Done", "status": "completed"}


@router.get("/sessions/{session_id}/result")
async def preluare_rezultat(session_id: str):
    sesiune = sesiuni_active.get(session_id)
    if not sesiune:
        raise HTTPException(status_code=404, detail="Invalid session")
    if sesiune["status"] != "completed":
        return {"status": sesiune["status"], "message": "Still processing"}
    return {"status": "completed", "data": sesiune["rezultat_final"]}
