# Metodologia de Evaluare — WER și DER

## 1. Prezentare Generală

Evaluarea sistemului Diagnostic Assistant utilizează două metrici principale:
- **WER** (Word Error Rate) — pentru calitatea transcrierii ASR
- **DER** (Diarization Error Rate) — pentru acuratețea atribuirii vorbitorului

---

## 2. Word Error Rate (WER)

### 2.1 Definiție

WER măsoară diferența dintre transcrierea automată și transcrierea de referință:

```
WER = (S + D + I) / N
```

unde:
- **S** = substituții (cuvânt înlocuit)
- **D** = ștergeri (cuvânt lipsă)
- **I** = inserții (cuvânt în plus)
- **N** = numărul total de cuvinte din referință

### 2.2 Implementare

Calculul WER utilizează biblioteca `jiwer`:

```python
from jiwer import wer, compute_measures
score = wer(reference_text, hypothesis_text)
measures = compute_measures(reference_text, hypothesis_text)
```

### 2.3 Obiective de Performanță

| Condiție | WER Țintă | WER Acceptabil |
|----------|-----------|----------------|
| Condiții acustice bune | < 10% | < 15% |
| Zgomot de fond moderat | < 20% | < 30% |
| Termeni medicali specifici | < 25% | < 35% |

### 2.4 Pre-procesare pentru Evaluare
- Normalizare text (lowercase, eliminare punctuație)
- Eliminare cuvinte de umplutură (ă, ăă, etc.)
- Normalizare numere (cifre → text)

---

## 3. Diarization Error Rate (DER)

### 3.1 Definiție

DER măsoară erorile în atribuirea vorbitorului:

```
DER = (FA + MISS + CONF) / Total_Duration
```

unde:
- **FA** (False Alarm) = timp atribuit vorbirii când nu există vorbire
- **MISS** (Missed Speech) = vorbire nedetectată
- **CONF** (Speaker Confusion) = vorbire atribuită vorbitorului greșit

### 3.2 Implementare

```python
from pyannote.metrics.diarization import DiarizationErrorRate
metric = DiarizationErrorRate()
der_score = metric(reference_annotation, hypothesis_annotation)
```

### 3.3 Obiective de Performanță

| Condiție | DER Țintă | DER Acceptabil |
|----------|-----------|----------------|
| 2 vorbitori, condiții bune | < 10% | < 20% |
| Suprapuneri de vorbire | < 20% | < 35% |
| Schimbări frecvente de vorbitor | < 15% | < 25% |

---

## 4. Scenarii de Test Incremental

### Scenariul 1 — Baseline (2 vorbitori, fără zgomot)
- **Descriere**: Consultație simulată în condiții ideale
- **Durată**: 5 minute
- **Vorbitori**: 1 doctor + 1 pacient, voci distincte
- **Metrici**: WER < 10%, DER < 10%

### Scenariul 2 — Zgomot de fond
- **Descriere**: Consultație cu zgomot de fond (aparate medicale, ventilatoare)
- **Durată**: 5 minute
- **SNR**: 15-20 dB
- **Metrici**: WER < 20%, DER < 20%

### Scenariul 3 — Terminologie medicală
- **Descriere**: Consultație cu termeni medicali specializați în română
- **Durată**: 5 minute
- **Vocabular special**: diagnostice, medicamente, proceduri
- **Metrici**: WER < 25%, DER < 15%

### Scenariul 4 — Suprapuneri de vorbire
- **Descriere**: Conversație cu întreruperi și suprapuneri frecvente
- **Durată**: 5 minute
- **Metrici**: WER < 25%, DER < 30%

### Scenariul 5 — Sesiune lungă
- **Descriere**: Consultație completă de 30 de minute
- **Durată**: 30 minute
- **Metrici**: WER < 15%, DER < 15%, latență < 3s

---

## 5. Date de Test

### 5.1 Surse de date
- Date sintetice generate cu TTS (Text-to-Speech) pentru validare
- Date anonimizate din consultații reale (cu consimțământ)
- Date publice din corpora medicale românești

### 5.2 Format date
- Audio: WAV, 16kHz, mono, 16-bit PCM
- Referință transcriere: format JSON cu timestamps
- Referință diarizare: format RTTM standard

### 5.3 Structura dataset de test
```
evaluation/datasets/
├── README.md           # Instrucțiuni
├── scenario_01/        # Baseline
│   ├── audio.wav
│   ├── reference.json
│   └── reference.rttm
└── scenario_0N/        # Scenariul N
```

---

## 6. Raportare Rezultate

Raportul de evaluare include:
- Tabel comparativ WER/DER per scenariu
- Grafice evoluție performanță
- Analiza tipurilor de erori
- Recomandări de îmbunătățire

Generare raport automat:
```bash
python scripts/run_evaluation.py --test-dir evaluation/datasets/
python scripts/generate_report.py --results-dir results/
```
