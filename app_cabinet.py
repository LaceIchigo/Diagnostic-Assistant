import sounddevice as sd
import numpy as np
import queue
import time
import torch
import os
import sys

# Importăm modulul nostru separat (Creierul)
from modul_llm import genereaza_raport_medical

# Ascundem avertismentele C++
stderr_original = sys.stderr
sys.stderr = open(os.devnull, 'w')
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
sys.stderr = stderr_original

audio_queue = queue.Queue()

def callback_microfon(indata, frames, time_info, status):
    audio_queue.put(indata.copy())

def curata_consola():
    os.system('cls' if os.name == 'nt' else 'clear')

def asistent_medical_hibrid(hf_token="PUNE_TOKENUL_TAU_AICI"):
    print("⏳ Încarc Whisper (Text) și Silero VAD (Viteză live)...")
    whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    
    vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)
    get_speech_timestamps = utils[0]

    SAMPLE_RATE = 16000
    PAS_VERIFICARE = 0.5
    MIN_CHUNK = 2.0
    MAX_CHUNK = 8.0
    
    buffer_curent = []
    istoric_audio_complet = []
    transcript_brut = [] 
    timp_total_inregistrat = 0.0
    
    curata_consola()
    print("======================================================")
    print(" 🏥 ASISTENT MEDICAL AI - MODULAR & STABIL ")
    print("======================================================")
    print("🟢 Consultația a început. (Textul va apărea instant)")
    print("   Apăsați Ctrl+C la final pentru Diarizare și Rezumat.\n")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=int(SAMPLE_RATE * PAS_VERIFICARE), 
                            channels=1, dtype='int16', callback=callback_microfon):
            
            while True:
                date_audio = audio_queue.get()
                buffer_curent.append(date_audio)
                istoric_audio_complet.append(date_audio) 
                
                chunk_curent_flat = np.concatenate(buffer_curent, axis=0).flatten()
                durata_curenta = len(chunk_curent_flat) / SAMPLE_RATE
                
                taiem_aici = False
                
                # Logica VAD
                if durata_curenta >= MAX_CHUNK:
                    taiem_aici = True
                elif durata_curenta >= MIN_CHUNK:
                    ultima_secunda = chunk_curent_flat[-SAMPLE_RATE:]
                    ultima_secunda_float = ultima_secunda.astype(np.float32) / 32768.0
                    vocile_gasite = get_speech_timestamps(torch.from_numpy(ultima_secunda_float), vad_model, sampling_rate=SAMPLE_RATE)
                    if not vocile_gasite:
                        taiem_aici = True

                # Procesare LIVE extrem de rapidă
                if taiem_aici:
                    chunk_nou_float32 = chunk_curent_flat.astype(np.float32) / 32768.0
                    
                    whisper_segments, _ = whisper_model.transcribe(
                        chunk_nou_float32, beam_size=5, language="ro", vad_filter=True
                    )
                    
                    for segment in whisper_segments:
                        text_curat = segment.text.strip()
                        if text_curat:
                            print(f"[{time.strftime('%H:%M:%S')}] Medic/Pacient: {text_curat}")
                            
                            start_real = timp_total_inregistrat + segment.start
                            end_real = timp_total_inregistrat + segment.end
                            transcript_brut.append({
                                "start": start_real, 
                                "end": end_real, 
                                "text": text_curat
                            })
                            
                    timp_total_inregistrat += durata_curenta
                    buffer_curent = []
                    
    except KeyboardInterrupt:
        print("\n\n🛑 Consultație încheiată.")
        print("⚙️ [1/2] Încep separarea vocilor (Diarizare pe CPU). Vă rugăm așteptați...")
        
        audio_complet_flat = np.concatenate(istoric_audio_complet, axis=0).flatten()
        audio_complet_float = audio_complet_flat.astype(np.float32) / 32768.0
        
        print("⏳ Încarc modelul de Diarizare Pyannote...")
        pyannote_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=hf_token)

        print("🔍 Analizez vocile din întreaga consultație...")
        waveform = torch.from_numpy(audio_complet_float).unsqueeze(0)
        
        start_diarizare = time.time()
        diarizare = pyannote_pipeline({"waveform": waveform, "sample_rate": SAMPLE_RATE}, num_speakers=2)
        print(f"⏱️ Diarizare finalizată în {time.time() - start_diarizare:.1f} secunde.")

        if hasattr(diarizare, "speaker_diarization"):
            diarizare = diarizare.speaker_diarization
            
        print("\n======================================================")
        print(" 📄 TRANSCRIPT FINAL (Separare pe vorbitori)")
        print("======================================================\n")
        
        transcript_text_pentru_llm = ""
        
        for item in transcript_brut:
            suprapunere_maxima = 0
            vorbitor = "NECUNOSCUT"
            
            for turn, _, speaker in diarizare.itertracks(yield_label=True):
                intersec_start = max(item["start"], turn.start)
                intersec_end = min(item["end"], turn.end)
                durata = intersec_end - intersec_start
                
                if durata > suprapunere_maxima:
                    suprapunere_maxima = durata
                    vorbitor = speaker
                    
            print(f"[{item['start']:05.2f}s - {item['end']:05.2f}s] {vorbitor}: {item['text']}")
            transcript_text_pentru_llm += f"{vorbitor}: {item['text']}\n"
            
        # ==========================================
        # Faza 4: Analiza LLM (Apelăm modulul extern)
        # ==========================================
        raport_final, timp_executie = genereaza_raport_medical(transcript_text_pentru_llm)
        
        print("\n======================================================")
        print(" 🏥 RAPORT MEDICAL FINAL")
        print("======================================================")
        print(raport_final)
        if timp_executie > 0:
            print(f"\n⏱️ Raport generat în {timp_executie:.1f} secunde.")
        
        # --- Salvare automată în fișier ---
        nume_fisier = f"Consultatie_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(nume_fisier, "w", encoding="utf-8") as fisier:
                fisier.write("TRANSCRIPT:\n")
                fisier.write(transcript_text_pentru_llm)
                fisier.write("\n\n=================================\n")
                fisier.write("RAPORT MEDICAL:\n")
                fisier.write(raport_final)
            print(f"💾 Datele au fost salvate automat în fișierul: {nume_fisier}")
        except Exception as e:
            print(f"⚠️ Nu am putut salva fișierul: {e}")

if __name__ == "__main__":
    TOKEN_HUGGINGFACE = "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" 
    asistent_medical_hibrid(hf_token=TOKEN_HUGGINGFACE)