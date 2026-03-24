import time
import torch
import numpy as np
from scipy.io import wavfile
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

def proceseaza_consultatie(nume_fisier="test_audio.wav"):
    start_total = time.time()
    
    # ==========================================
    # 1. ÎNCĂRCAREA MODELELOR (RAM Intensiv)
    # ==========================================
    print("⏳ [1/4] Încarc modelele AI în memorie...")
    # Whisper
    whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    
    # Pyannote (PUNE TOKEN-UL TĂU AICI)
    TOKEN_HF = "PUNE_TOKENUL_TAU_AICI"
    pyannote_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=TOKEN_HF)
    
    # ==========================================
    # 2. TRANSCRIEREA (WHISPER)
    # ==========================================
    print(f"\n📝 [2/4] Transcriere audio ({nume_fisier})...")
    context_medical = "Acesta este un dialog medical în limba română între un medic și un pacient."
    whisper_segments, _ = whisper_model.transcribe(
        nume_fisier, beam_size=5, language="ro", vad_filter=True, initial_prompt=context_medical
    )
    
    # Salvăm segmentele Whisper într-o listă pentru a le putea parcurge mai târziu
    segmente_text = list(whisper_segments) 

    # ==========================================
    # 3. DIARIZAREA (PYANNOTE cu Bypass SciPy)
    # ==========================================
    print("\n🗣️ [3/4] Identificarea vorbitorilor (Diarizare)...")
    sample_rate, data = wavfile.read(nume_fisier)
    data_float = data.astype(np.float32) / 32768.0
    waveform = torch.from_numpy(data_float).unsqueeze(0)
    
    audio_in_memory = {"waveform": waveform, "sample_rate": sample_rate}
    diarizare = pyannote_pipeline(audio_in_memory, num_speakers=2)
    
    # Adaptare pentru Pyannote 4.x
    if hasattr(diarizare, "speaker_diarization"):
        diarizare = diarizare.speaker_diarization

    # ==========================================
    # 4. ALINIEREA (FUZIUNEA DATELOR)
    # ==========================================
    print("\n🔗 [4/4] Aliniere text cu vorbitori...")
    print("-" * 50)
    
    transcript_final = []

    # Parcurgem fiecare frază găsită de Whisper
    for segment in segmente_text:
        seg_start = segment.start
        seg_end = segment.end
        text_sters = segment.text.strip()
        
        suprapunere_maxima = 0
        vorbitor_ales = "NECUNOSCUT"
        
        # Parcurgem toți vorbitorii găsiți de Pyannote
        for turn, _, speaker in diarizare.itertracks(yield_label=True):
            # Calculăm intersecția timpilor (cât se suprapun cele două intervale)
            timp_start_comun = max(seg_start, turn.start)
            timp_end_comun = min(seg_end, turn.end)
            durata_suprapunere = timp_end_comun - timp_start_comun
            
            # Dacă există o suprapunere reală și e mai mare decât ce am găsit până acum
            if durata_suprapunere > suprapunere_maxima:
                suprapunere_maxima = durata_suprapunere
                vorbitor_ales = speaker
                
        # Construim linia finală de text
        linie_formatata = f"[{seg_start:05.2f}s - {seg_end:05.2f}s] {vorbitor_ales}: {text_sters}"
        transcript_final.append(linie_formatata)
        print(linie_formatata)

    print("-" * 50)
    print(f"✅ GATA! Procesare completă în {time.time() - start_total:.2f} secunde.")
    
    return transcript_final

if __name__ == "__main__":
    proceseaza_consultatie("test_audio.wav")