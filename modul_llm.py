import ollama
import time

# Minimum recommended: llama3.1:8b
# Best results:        llama3.1:70b  (needs ~40GB RAM)
# Fastest acceptable:  llama3.1:8b   (needs ~6GB RAM)
MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are a clinical decision-support AI embedded in a doctor's consultation room.
Your only job is to analyze the conversation transcript provided and produce a structured medical report.

STRICT RULES — follow these without exception:
- Base EVERY statement exclusively on what was said in the transcript.
- If a piece of information was NOT mentioned in the transcript, write "Not mentioned" — never invent or infer it.
- Do not add symptoms, diagnoses, medications, or history that are not explicitly present in the dialogue.
- Do not speculate beyond what the speakers actually said.
- Identify speakers by their role (Doctor / Patient), inferred from context (who asks questions vs. who describes symptoms).

OUTPUT FORMAT — use exactly these sections:

## 1. Speaker Identification
State which SPEAKER label (e.g. SPEAKER_00) is the Doctor and which is the Patient, and briefly explain how you identified them.

## 2. Chief Complaint
One sentence summarising why the patient came in, in the patient's own words if possible.

## 3. Symptom Summary
List only symptoms explicitly mentioned in the transcript.
- Confirmed: symptoms the patient affirmed they have
- Denied: symptoms the patient said they do not have
- Duration / onset: only if stated

## 4. Relevant History
Only information actually mentioned: medications, allergies, past conditions, family history.
Write "Not mentioned" for anything absent.

## 5. Differential Diagnosis
Provide 2–4 possible diagnoses ranked by likelihood based ONLY on the symptoms confirmed above.
For each:
  - Name of condition
  - Supporting evidence FROM THE TRANSCRIPT (quote or paraphrase what was said)
  - Missing information that would help confirm or rule it out

## 6. Suggested Next Steps
Only suggest investigations or referrals that are clinically logical given the confirmed symptoms.
Do not invent standard protocols — only recommend what the transcript's symptom picture justifies.

## 7. Disclaimer
This report is an AI-generated summary of a medical conversation and is intended to assist — not replace — clinical judgement. It must be reviewed and verified by a licensed medical professional before any clinical decision is made.
"""

def genereaza_raport_medical(transcript_text: str):
    """
    Receives the diarized transcript and returns a structured differential diagnosis report.
    """
    if not transcript_text or not transcript_text.strip():
        return "⚠️ Empty transcript — no report generated.", 0.0

    print(f"\n⚙️  Generating medical report with {MODEL}...")
    print(f"    Transcript length: {len(transcript_text.split())} words")

    user_message = f"""Here is the transcript from the medical consultation. Analyze it and produce the report.

TRANSCRIPT:
{transcript_text}

Remember: only use information present in the transcript above. Do not add anything that was not said."""

    try:
        start = time.time()
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            options={
                "temperature": 0.1,   # low temperature = less hallucination
                "top_p": 0.9,
                "num_predict": 2048,
            }
        )
        raport = response["message"]["content"]
        elapsed = time.time() - start
        print(f"✅ Report generated in {elapsed:.1f}s")
        return raport, elapsed

    except Exception as e:
        error_msg = f"❌ Ollama error ({MODEL}): {e}\nMake sure Ollama is running: `ollama serve`"
        print(error_msg)
        return error_msg, 0.0