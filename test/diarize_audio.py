from pyannote.audio import Pipeline
import torch
from scipy.io import wavfile
import numpy as np
import time

def diarizeaza_audio(nume_fisier="test_audio.wav", hf_token="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"):
    print("⏳ Încarc modelul Pyannote...")
    start_time = time.time()
    
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token  # <--- Aici e singura modificare
        )
        
        print(f"\n📁 Citesc manual fișierul cu SciPy (ocolim eroarea torchcodec): {nume_fisier}")
        
        # 1. Citim fișierul cu SciPy
        sample_rate, data = wavfile.read(nume_fisier)
        
        # 2. Convertim datele în float32 (numere între -1.0 și 1.0)
        data_float = data.astype(np.float32) / 32768.0
        
        # 3. Creăm tensorul PyTorch. 
        # ATENȚIE: Pyannote vrea formatul (canale, timp). 
        # SciPy ne dă doar o listă plată de tipul (timp,), așa că folosim unsqueeze(0) 
        # pentru a adăuga „canalul” lipsă (1 canal mono).
        waveform = torch.from_numpy(data_float).unsqueeze(0)
        
        # 4. Împachetăm totul în dicționarul magic cerut de Pyannote
        audio_in_memory = {
            "waveform": waveform,
            "sample_rate": sample_rate
        }
        
        print("🧠 Încep procesarea acustică (căutăm vorbitorii)...")
        # 5. Pasăm dicționarul către pipeline în loc să dăm numele fișierului!
        diarizare = pipeline(audio_in_memory, num_speakers=2)
        
        print("\n✅ Rezultatul diarizării (Cine a vorbit și când):")
        print("-" * 40)
        
        # Extragem adnotarea din "ambalajul" versiunii noi (Pyannote 4.x)
        if hasattr(diarizare, "speaker_diarization"):
            diarizare = diarizare.speaker_diarization

        # Acum putem itera fără probleme!
        for turn, _, speaker in diarizare.itertracks(yield_label=True):
            print(f"[{turn.start:.2f}s - {turn.end:.2f}s] {speaker}")
            
    except Exception as e:
        print("\n❌ A apărut o eroare!")
        print(f"Detalii eroare: {e}")
        
    end_time = time.time()
    print("-" * 40)
    print(f"⏱️ Timp de procesare: {end_time - start_time:.2f} secunde.")

if __name__ == "__main__":
    # ATENȚIE: Pune tokenul tău real mai jos!
    TOKEN_HUGGINGFACE = "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" 
    
    diarizeaza_audio(hf_token=TOKEN_HUGGINGFACE)