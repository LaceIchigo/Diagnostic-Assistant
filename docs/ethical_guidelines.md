# Ghid de Principii Etice — Diagnostic Assistant

## 1. Introducere

Sistemul **Diagnostic Assistant** a fost conceput și implementat cu respectarea strictă a principiilor etice în domeniul inteligenței artificiale aplicate în medicină, conform:
- Regulamentului General privind Protecția Datelor (GDPR) — Regulamentul UE 2016/679
- Legii nr. 190/2018 privind măsuri de punere în aplicare a GDPR în România
- Ghidurilor etice AI ale Comisiei Europene (Ethics Guidelines for Trustworthy AI)
- Codului Deontologic al Medicului din România

---

## 2. Principii Fundamentale

### 2.1 Confidențialitatea Datelor

**Modelul nu are acces la date personale identificabile.**

Sistemul procesează exclusiv semnalul audio brut în timp real, fără:
- Stocare permanentă a înregistrărilor audio
- Transmitere de date audio sau text în servicii cloud externe
- Asociere automată cu dosare medicale sau identități ale pacienților
- Colectare de metadate identificabile (IP, locație, etc.)

Toate datele audio sunt procesate local, pe dispozitivul medicului, și nu părăsesc infrastructura cabinetului medical.

### 2.2 Abstractizarea și Anonimizarea

**Învățarea se face exclusiv pe date abstractizate.**

Orice proces de fine-tuning sau îmbunătățire a modelelor utilizate se realizează pe:
- Date anonimizate și de-identificate conform standardelor medicale
- Seturi de date sintetice generate pentru validare
- Date publice autorizate pentru cercetare medicală

Nu se utilizează date reale ale pacienților pentru antrenare fără consimțământ explicit și anonimizare prealabilă.

### 2.3 Responsabilitatea Medicală

**Decizia medicală finală aparține exclusiv medicului.**

Sistemul Diagnostic Assistant:
- NU emite diagnostice medicale
- NU recomandă tratamente sau medicamente
- NU înlocuiește judecata clinică a medicului
- NU trebuie utilizat ca unică sursă de informație medicală

Transcrierea automată este un instrument de suport documentar, nu un instrument de diagnostic.

### 2.4 Rolul Sistemului

**Sistemul are rol de suport și standardizare a informației.**

Scopul explicit al sistemului este:
- Reducerea sarcinii administrative a medicilor
- Standardizarea documentației consultațiilor
- Facilitarea accesului la informații în cadrul consultației
- Îmbunătățirea calității documentației medicale

Orice utilizare a sistemului în afara acestor scopuri declarate reprezintă o utilizare improprie.

---

## 3. Transparență și Consimțământ

### 3.1 Informarea Pacienților
- Pacienții **trebuie** informați că consultația este înregistrată și transcrisă automat
- Consimțământul explicit al pacientului trebuie obținut înainte de utilizarea sistemului
- Pacientul are dreptul de a refuza înregistrarea fără consecințe asupra îngrijirii medicale

### 3.2 Drepturile Pacienților (GDPR)
- Dreptul de acces la datele proprii
- Dreptul la rectificare a transcrierii incorecte
- Dreptul la ștergerea datelor (dreptul de a fi uitat)
- Dreptul la portabilitate a datelor

---

## 4. Limitări Tehnice Cunoscute

Utilizatorii sistemului trebuie informați cu privire la limitările cunoscute:

| Limitare | Impact | Recomandare |
|----------|--------|-------------|
| Acuratețe ASR ~85-95% | Text poate conține erori | Medicul verifică transcrierea |
| Diarizare poate confunda vorbitorii | Atribuire incorectă de roluri | Corecție manuală disponibilă |
| Performanță redusă în zgomot | Transcriere incompletă | Utilizare în condiții acustice bune |
| Suport limitat dialecte românești | Acuratețe variabilă regional | Raportare erori pentru îmbunătățire |

---

## 5. Securitate

- Transcrierea se salvează local, cu acces restricționat
- Fișierele de transcriere nu conțin date biometrice
- Se recomandă criptarea stocării locale (BitLocker, LUKS)
- Accesul la sistem este restricționat la personal medical autorizat

---

## 6. Audit și Responsabilitate

- Sistemul înregistrează activitatea (fără date personale) pentru audit tehnic
- Erorile de transcriere pot fi raportate pentru îmbunătățirea modelelor
- Responsabilitatea utilizării corecte revine instituției medicale

---

## 7. Revizuire Etică

Acest document va fi revizuit semestrial sau la apariția oricăror modificări semnificative ale sistemului. Orice modificare care afectează principiile etice declarate necesită consultarea unui comitet de etică medical.

---

*Ultima actualizare: 2024*
*Versiune document: 1.0*
