import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np

def inregistreaza_audio(nume_fisier="test_audio.wav", durata_secunde=10):
    # Setări CRUCIALE pentru modelele AI (Silero VAD și Whisper)
    # Aceste modele au fost antrenate pe audio la 16kHz, mono. 
    # Dacă folosim 44.1kHz (calitate CD), modelele vor da rezultate proaste sau erori.
    SAMPLE_RATE = 16000 
    CHANNELS = 1

    print(f"🎤 Încep înregistrarea pentru {durata_secunde} secunde...")
    print("Vorbește la microfon (ex: 'Bună ziua, mă doare capul și am febră.')...")

    # Pornim înregistrarea
    # dtype='int16' este formatul standard PCM necesar pentru majoritatea modelelor
    inregistrare = sd.rec(
        int(durata_secunde * SAMPLE_RATE), 
        samplerate=SAMPLE_RATE, 
        channels=CHANNELS, 
        dtype=np.int16
    )
    
    # Așteptăm ca înregistrarea să se termine (blochează execuția până trec secundele)
    sd.wait() 
    print("✅ Înregistrare finalizată!")

    # Salvăm fișierul pe disc
    write(nume_fisier, SAMPLE_RATE, inregistrare)
    print(f"💾 Fișierul a fost salvat ca: {nume_fisier}")

if __name__ == "__main__":
    inregistreaza_audio()