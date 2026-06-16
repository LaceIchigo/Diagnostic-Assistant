"""
scripts/migrare_gdpr.py — Migrare baza de date la schema GDPR.

Ce face:
  1. Genereaza si salveaza ENCRYPTION_KEY + CNP_SALT in .env daca lipsesc
  2. Face backup la cabinet.db
  3. Adauga coloanele GDPR lipsa (cnp_masked, consent_gdpr, data_consent)
  4. Hash-uieste CNP-urile plaintext existente
  5. Cripteaza campurile de consultatie necriptate

Rulare (din radacina proiectului):
    python scripts/migrare_gdpr.py
"""
import os
import sys
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Pas 1: Asigura .env cu cheile necesare ──────────────────────────────────

env_path = Path(".env")
env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

updated = False

if "ENCRYPTION_KEY=" not in env_content:
    from cryptography.fernet import Fernet
    new_key = Fernet.generate_key().decode()
    env_content += f"\nENCRYPTION_KEY={new_key}"
    updated = True
    print("[OK] ENCRYPTION_KEY generata si adaugata in .env")

if "CNP_SALT=" not in env_content:
    import secrets
    new_salt = "salt_" + secrets.token_hex(16)
    env_content += f"\nCNP_SALT={new_salt}"
    updated = True
    print("[OK] CNP_SALT generat si adaugat in .env")

if updated:
    env_path.write_text(env_content.strip() + "\n", encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(override=True)

from services.gdpr_service import gdpr

# ── Pas 2: Backup cabinet.db ────────────────────────────────────────────────

db_path = Path("cabinet.db")
if not db_path.exists():
    print("[INFO] cabinet.db nu exista — nimic de migrat.")
    print("[OK] Migrare completa (baza de date goala, schema noua va fi creata la pornire).")
    exit(0)

ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_path = Path(f"cabinet_backup_{ts}.db")
shutil.copy2(db_path, backup_path)
print(f"[OK] Backup salvat: {backup_path}")

# ── Pas 3: Adauga coloane lipsa ─────────────────────────────────────────────

conn = sqlite3.connect("cabinet.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(pacienti)")}

migrations = []
if "cnp_masked" not in existing_cols:
    migrations.append("ALTER TABLE pacienti ADD COLUMN cnp_masked TEXT DEFAULT ''")
if "consent_gdpr" not in existing_cols:
    migrations.append("ALTER TABLE pacienti ADD COLUMN consent_gdpr INTEGER DEFAULT 0")
if "data_consent" not in existing_cols:
    migrations.append("ALTER TABLE pacienti ADD COLUMN data_consent TEXT")

for sql in migrations:
    cur.execute(sql)
    print(f"[OK] Schema: {sql}")

conn.commit()

# ── Pas 4: Hash CNP-uri plaintext ───────────────────────────────────────────

pacienti = cur.execute("SELECT id, cnp, cnp_masked FROM pacienti").fetchall()
hashed_count = 0

for row in pacienti:
    cnp_val = row["cnp"] or ""
    if len(cnp_val) == 13 and cnp_val.isdigit():
        cnp_hash = gdpr.hash_cnp(cnp_val)
        cnp_masked = gdpr.mask_cnp(cnp_val)
        cur.execute(
            "UPDATE pacienti SET cnp=?, cnp_masked=?, consent_gdpr=1 WHERE id=?",
            (cnp_hash, cnp_masked, row["id"]),
        )
        hashed_count += 1

conn.commit()
print(f"[OK] CNP-uri hash-uite: {hashed_count}")

# ── Pas 5: Cripteaza campurile de consultatie necriptate ────────────────────

consultatii = cur.execute(
    "SELECT id, transcript_audio, rezumat_diagnostic, raport_corectat_medic FROM consultatii"
).fetchall()

encrypted_count = 0

for row in consultatii:
    changes = {}
    for col in ("transcript_audio", "rezumat_diagnostic", "raport_corectat_medic"):
        val = row[col]
        if not val:
            continue
        try:
            gdpr.fernet.decrypt(val.encode("utf-8"))
        except Exception:
            changes[col] = gdpr.encrypt(val)

    if changes:
        set_clause = ", ".join(f"{k}=?" for k in changes)
        cur.execute(
            f"UPDATE consultatii SET {set_clause} WHERE id=?",
            (*changes.values(), row["id"]),
        )
        encrypted_count += 1

conn.commit()
conn.close()
print(f"[OK] Consultatii criptate: {encrypted_count}")
print()
print("[DONE] Migrare GDPR completa!")
print(f"   Backup:          {backup_path}")
print(f"   CNP-uri hash:    {hashed_count}")
print(f"   Consultatii enc: {encrypted_count}")
