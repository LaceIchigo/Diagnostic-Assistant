# Date de Evaluare — Diagnostic Assistant

## Prezentare Generală

Acest director conține datele de test pentru evaluarea sistemului Diagnostic Assistant.
Din motive de confidențialitate și GDPR, **nu sunt incluse fișiere audio reale** cu consultații medicale.

## Structura Așteptată

```
datasets/
├── 01_baseline/
│   ├── audio.wav          # WAV 16kHz mono (date sintetice sau anonimizate)
│   ├── reference.txt      # Transcript de referință (text simplu)
│   └── reference.rttm     # Referință diarizare în format RTTM
├── 02_background_noise/
│   ├── audio.wav
│   ├── reference.txt
│   └── reference.rttm
├── 03_medical_terminology/
│   ├── audio.wav
│   ├── reference.txt
│   └── reference.rttm
├── 04_overlapping_speech/
│   ├── audio.wav
│   ├── reference.txt
│   └── reference.rttm
└── 05_long_session/
    ├── audio.wav
    ├── reference.txt
    └── reference.rttm
```

## Format Fișiere

### Audio (audio.wav)
- Format: WAV PCM 16-bit
- Frecvență eșantionare: 16000 Hz
- Canale: 1 (mono)

### Transcript de referință (reference.txt)
Text simplu, o linie per segment sau continuu. Exemplu:
```
Bună ziua, ce probleme aveți astăzi?
Am dureri de cap de trei zile.
De când exact? Dimineața sau pe tot parcursul zilei?
Mai ales dimineața, când mă trezesc.
```

### Format RTTM (reference.rttm)
Standard NIST RTTM:
```
SPEAKER <filename> 1 <onset> <duration> <NA> <NA> <speaker> <NA> <NA>
```
Exemplu:
```
SPEAKER consultatie_01 1 0.000 5.230 <NA> <NA> SPEAKER_00 <NA> <NA>
SPEAKER consultatie_01 1 5.500 4.100 <NA> <NA> SPEAKER_01 <NA> <NA>
```

unde SPEAKER_00 = Doctor, SPEAKER_01 = Pacient.

## Generare Date Sintetice

Pentru teste fără date reale, puteți genera audio sintetic cu TTS:

```python
from gtts import gTTS
import numpy as np
import scipy.io.wavfile

# Doctor
tts_doctor = gTTS("Bună ziua, ce probleme aveți astăzi?", lang='ro')
tts_doctor.save("doctor.mp3")

# Pacient
tts_patient = gTTS("Am dureri de cap de trei zile.", lang='ro')
tts_patient.save("patient.mp3")
```

## Adăugare Date Reale

Dacă doriți să adăugați date din consultații reale:
1. Obțineți consimțământul explicit al pacienților și medicilor
2. Anonimizați toate datele personale identificabile
3. Verificați conformitatea GDPR înainte de orice utilizare
4. Nu comiteți date cu informații personale în repository

**Modelul nu are acces la date personale identificabile.**
