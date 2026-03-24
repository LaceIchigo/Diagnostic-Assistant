from faster_whisper import WhisperModel
import time

def transcrie_audio(nume_fisier="test_audio.wav"):
    # 1. Am crescut modelul la "small" (descarcă aprox. 500MB prima dată)
    model_size = "small" 
    
    print(f"⏳ Încarc modelul Whisper ({model_size})...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"📁 Încep transcrierea: {nume_fisier}")
    start_time = time.time()

    # Contextul nostru medical pentru a ghida modelul
    context_medical = "Acesta este un dialog medical în limba română între un medic și un pacient. Se discută despre simptome, dureri, febră, rețete și diagnostic."

    # 2 & 3. Am adăugat vad_filter și initial_prompt
    segments, info = model.transcribe(
        nume_fisier, 
        beam_size=5, 
        language="ro",
        vad_filter=True, # Curăță zgomotul de fundal
        initial_prompt=context_medical # Setează vocabularul
    )

    print("-" * 30)
    for segment in segments:
        print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")

    end_time = time.time()
    print("-" * 30)
    print(f"⏱️ Timp de procesare: {end_time - start_time:.2f} secunde.")

if __name__ == "__main__":
    transcrie_audio()