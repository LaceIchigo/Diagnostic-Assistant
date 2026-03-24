from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
import sys
import time

# --- IMPORTĂM MODELELE AI ---
from modul_llm import genereaza_raport_medical

stderr_original = sys.stderr
sys.stderr = open(os.devnull, 'w')
from faster_whisper import WhisperModel
# Am lăsat Pyannote importat doar la final pentru a nu bloca memoria
sys.stderr = stderr_original

# Încărcăm Whisper o singură dată când pornește serverul
print("⏳ Încarc modelul Whisper...")
whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
print("✅ Whisper este gata!")

app = FastAPI(title="API Asistent Medical AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baza de date în memorie
sesiuni_active = {}
TOKEN_HUGGINGFACE = "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" # Tokenul tău

class SessionResponse(BaseModel):
    session_id: str
    status: str

@app.post("/sessions", response_model=SessionResponse)
async def creare_sesiune():
    session_id = str(uuid.uuid4())
    sesiuni_active[session_id] = {
        "status": "created",
        "audio_bytes": bytearray(),
        "transcript_complet": "",
        "rezultat_final": None
    }
    return {"session_id": session_id, "status": "created"}

@app.websocket("/sessions/{session_id}/stream")
async def websocket_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    if session_id not in sesiuni_active:
        await websocket.close()
        return

    sesiuni_active[session_id]["status"] = "streaming"
    temp_audio_path = f"live_audio_{session_id}.webm"

    try:
        while True:
            # 1. Primim binarul (sunetul) de la React
            chunk_bytes = await websocket.receive_bytes()
            
            # 2. Îl adăugăm la înregistrarea completă a sesiunii
            sesiuni_active[session_id]["audio_bytes"].extend(chunk_bytes)
            
            # 3. Salvăm progresul într-un fișier fizic pentru ca Whisper să-l poată citi
            with open(temp_audio_path, "wb") as f:
                f.write(sesiuni_active[session_id]["audio_bytes"])
            
            # 4. Rulăm Whisper pe fișierul actualizat
            segments, _ = whisper_model.transcribe(temp_audio_path, language="ro")
            
            text_curent = ""
            for segment in segments:
                text_curent += segment.text + " "
            
            text_curent = text_curent.strip()
            
            # 5. Trimitem transcriptul înapoi către interfață (doar dacă avem text nou)
            if text_curent and text_curent != sesiuni_active[session_id]["transcript_complet"]:
                sesiuni_active[session_id]["transcript_complet"] = text_curent
                await websocket.send_json({
                    "type": "partial_transcript",
                    "text": text_curent
                })
                
    except WebSocketDisconnect:
        print(f"🔴 Conexiune live întreruptă (Sesiune: {session_id})")

@app.post("/sessions/{session_id}/stop")
async def oprire_sesiune(session_id: str):
    if session_id not in sesiuni_active:
        raise HTTPException(status_code=404, detail="Sesiune invalidă")
    
    sesiuni_active[session_id]["status"] = "processing"
    transcript_brut = sesiuni_active[session_id]["transcript_complet"]
    temp_audio_path = f"live_audio_{session_id}.webm"
    
    print(f"⚙️ Procesez sesiunea {session_id}...")
    
    # === AICI AR FI VENIT PYANNOTE ===
    # NOTĂ PENTRU TEZĂ: Pyannote procesează fișiere .wav, iar browserul ne-a dat .webm.
    # Pentru a rula Diarizarea aici, ar trebui să folosim FFmpeg ca să convertim WebM în WAV.
    # Pentru moment, vom da transcriptul brut direct către Ollama pentru a obține diagnosticul rapid!
    
    print("🧠 Trimit transcriptul către Ollama pentru raport medical...")
    # COD VECHI:
    # raport_text, timp_executie = genereaza_raport_medical(transcript_brut)
    
    # COD NOU (Test Hardcodat):
    test_transcript = "Pacientul: Bună ziua, mă doare capul foarte tare de 3 zile și am febră 38. Medicul: Ați luat ceva pentru febră? Pacientul: Da, un paracetamol, dar nu a trecut. Medicul: Vă voi prescrie un antiinflamator mai puternic."
    print("🧠 Trimit transcriptul de TEST către Ollama...")
    raport_text, timp_executie = genereaza_raport_medical(test_transcript)
    # Curățăm fișierul audio temporar ca să nu umplem hard disk-ul
    try:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    except:
        pass

    sesiuni_active[session_id]["rezultat_final"] = {
        "summary": raport_text,
        "suggestions": ["(Vezi detaliile în raportul principal)"],
        "disclaimer": f"Timp de procesare LLM: {timp_executie:.1f} secunde."
    }
    sesiuni_active[session_id]["status"] = "completed"
    
    return {"message": "Procesare finalizată", "status": "completed"}

@app.get("/sessions/{session_id}/result")
async def preluare_rezultat(session_id: str):
    sesiune = sesiuni_active.get(session_id)
    if not sesiune:
        raise HTTPException(status_code=404, detail="Sesiune invalidă")
    if sesiune["status"] != "completed":
        return {"status": sesiune["status"], "message": "Procesare în curs"}
    return {"status": "completed", "data": sesiune["rezultat_final"]}

if __name__ == "__main__":
    import uvicorn
    print("🚀 API Medical pornit! Port: 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)