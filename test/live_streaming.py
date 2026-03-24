import sounddevice as sd
import numpy as np
import queue
import time

# Aceasta este "găleata" noastră thread-safe. 
# Microfonul va pune date aici, iar noi le vom scoate pentru procesare.
audio_queue = queue.Queue()

def callback_microfon(indata, frames, time_info, status):
    """
    Această funcție rulează pe un THREAD SEPARAT creat automat de sounddevice.
    Este apelată de zeci de ori pe secundă cu bucățele noi de audio.
    """
    if status:
        print(f"Avertisment microfon: {status}", flush=True)
        
    # Punem o copie a datelor primite în coadă
    audio_queue.put(indata.copy())

def porneste_sistem_live():
    print("🎤 Sistemul LIVE a pornit! Vorbește la microfon...")
    print("   (Apasă Ctrl+C în terminal pentru a opri)\n")
    
    SAMPLE_RATE = 16000
    CHANNELS = 1
    DURATA_CHUNK = 5  # Procesăm datele în ferestre de 5 secunde
    
    buffer_curent = []
    sample_uri_colectate = 0
    sample_uri_tinta = SAMPLE_RATE * DURATA_CHUNK # Câte numere înseamnă 5 secunde
    
    try:
        # InputStream deschide microfonul în fundal (non-blocking)
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, 
                            dtype='int16', callback=callback_microfon):
            
            # Bucla principală (Aici va trăi AI-ul nostru mai târziu)
            while True:
                # .get() așteaptă (blochează) până când apar date noi în coadă
                date_audio = audio_queue.get()
                buffer_curent.append(date_audio)
                sample_uri_colectate += len(date_audio)
                
                # Am strâns suficiente date pentru o fereastră (ex: 5 secunde)?
                if sample_uri_colectate >= sample_uri_tinta:
                    # Unim toate bucățelele într-un singur bloc (chunk) solid
                    chunk_audio = np.concatenate(buffer_curent, axis=0)
                    
                    # --- AICI VINE MAGIA ÎN PASUL URMĂTOR ---
                    print(f"📦 [CHUNK NOU] Am colectat un pachet de {DURATA_CHUNK} secunde de audio.")
                    print("   -> (Aici vom apela Whisper și Pyannote în curând...)")
                    # ----------------------------------------
                    
                    # Resetăm bufferul pentru următoarele 5 secunde
                    buffer_curent = []
                    sample_uri_colectate = 0
                    
    except KeyboardInterrupt:
        print("\n🛑 Sistem oprit manual de utilizator.")

if __name__ == "__main__":
    porneste_sistem_live()