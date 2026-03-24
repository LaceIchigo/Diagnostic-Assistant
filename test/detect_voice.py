import torch
from scipy.io import wavfile
import numpy as np

def detecteaza_vocea(nume_fisier="test_audio.wav"):
    print("⏳ Încarc modelul Silero VAD...")
    
    # Încărcăm modelul
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        trust_repo=True
    )

    # Extragem doar funcția de timestamp-uri (ignoram funcția read_audio care era stricată)
    get_speech_timestamps = utils[0] 

    print(f"📁 Citesc fișierul audio cu SciPy (bypass la eroarea torchaudio): {nume_fisier}")
    
    # 1. Citim fișierul cu scipy.io.wavfile (super stabil pe Windows)
    sample_rate, data = wavfile.read(nume_fisier)
    
    # 2. Silero VAD vrea datele sub formă de numere cu zecimale (float32) între -1.0 și 1.0. 
    # Noi le-am salvat ca int16. Așa că facem conversia matematică:
    data_float = data.astype(np.float32) / 32768.0
    
    # 3. Convertim array-ul într-un Tensor PyTorch
    wav_tensor = torch.from_numpy(data_float)

    print("🔍 Analizez unde se află voce umană...")
    # Trimitem tensorul creat de noi către model
    speech_timestamps = get_speech_timestamps(wav_tensor, model, sampling_rate=16000)

    if not speech_timestamps:
        print("🔇 Nu am detectat nicio voce în acest fișier.")
        return

    print("\n✅ Am detectat voce în următoarele intervale:")
    for segment in speech_timestamps:
        start_secunde = segment['start'] / 16000
        end_secunde = segment['end'] / 16000
        print(f"   🗣️ Voce de la {start_secunde:.2f}s până la {end_secunde:.2f}s")

if __name__ == "__main__":
    detecteaza_vocea()