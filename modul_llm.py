import ollama
import time

def genereaza_raport_medical(transcript_text):
    """
    Primește transcriptul brut și returnează raportul medical formatat folosind Ollama.
    """
    print("\n⚙️ [2/2] Generez Raportul Medical (Ollama - Llama 3.1)...")
    
    prompt_sistem = """
    Ești un asistent medical AI. Analizează următorul dialog dintr-un cabinet medical și generează un raport în limba română cu următoarele secțiuni:
    1. ROLURI: Identifică din context care SPEAKER este Medicul și care e Pacientul.
    2. MOTIVUL PREZENTĂRII: Rezumă scurt problema.
    3. SIMPTOME: Listă cu buline (confirmate și negate).
    4. SUGESTII DIAGNOSTIC: 2-3 posibile afecțiuni generale.
    5. AVERTISMENT: Disclaimer standard că acesta e un rezumat AI.
    """
    
    try:
        start_llm = time.time()
        response = ollama.chat(model='llama3.2:1b', messages=[
            {'role': 'system', 'content': prompt_sistem},
            {'role': 'user', 'content': transcript_text}
        ])
        
        raport_final = response['message']['content']
        timp_executie = time.time() - start_llm
        
        return raport_final, timp_executie
        
    except Exception as e:
        return f"❌ Eroare la conectarea cu Ollama: {e}", 0.0