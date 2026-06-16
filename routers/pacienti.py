from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from models.database import get_db, Pacient, Consultatie
from schemas.pacient import PacientNou
from services.gdpr_service import gdpr

router = APIRouter(tags=["Pacienti"])


@router.post("/pacienti")
def adauga_pacient(pacient: PacientNou, db: Session = Depends(get_db)):
    db_pacient = Pacient(
        nume_complet=pacient.nume_complet,
        cnp=gdpr.hash_cnp(pacient.cnp),
        cnp_masked=gdpr.mask_cnp(pacient.cnp),
        varsta=pacient.varsta,
        istoric_medical=pacient.istoric_medical,
        consent_gdpr=True,
        data_consent=datetime.now(timezone.utc),
    )
    db.add(db_pacient)
    db.commit()
    db.refresh(db_pacient)
    gdpr.log_access("PATIENT_CREATED", "medic", f"Pacient ID {db_pacient.id} inregistrat")
    return {"message": "Pacient adaugat!", "id": db_pacient.id}


@router.get("/pacienti")
def lista_pacienti(db: Session = Depends(get_db)):
    return db.query(Pacient).all()


@router.get("/pacienti/{pacient_id}/consultatii")
def get_consultatii_pacient(pacient_id: int, db: Session = Depends(get_db)):
    pacient = db.query(Pacient).filter(Pacient.id == pacient_id).first()
    if not pacient:
        raise HTTPException(status_code=404, detail="Pacientul nu exista")

    consultatii = (
        db.query(Consultatie)
        .filter(Consultatie.pacient_id == pacient_id)
        .order_by(Consultatie.data_consultatiei.desc())
        .all()
    )

    def decode(text):
        return gdpr.decrypt(text) if text else ""

    result = []
    for c in consultatii:
        diagnostic = decode(c.rezumat_diagnostic)
        rezumat_scurt = diagnostic[:200].strip()
        if len(diagnostic) > 200:
            rezumat_scurt += "..."
        result.append({
            "id": c.id,
            "data_consultatiei": str(c.data_consultatiei),
            "rezumat_scurt": rezumat_scurt,
            "diagnostic_complet": diagnostic,
            "transcript": decode(c.transcript_audio),
            "corectie_medic": decode(c.raport_corectat_medic),
            "are_corectie": bool(c.raport_corectat_medic),
            "utilizat_fl": bool(c.utilizat_pentru_fl),
            "sugestii": c.sugestii_tratament or "",
        })

    return {
        "pacient": {
            "id": pacient.id,
            "nume_complet": pacient.nume_complet,
            "varsta": pacient.varsta,
            "cnp_masked": pacient.cnp_masked or "***",
            "istoric_medical": pacient.istoric_medical or "",
        },
        "consultatii": result,
        "total": len(result),
    }


@router.get("/pacienti/{pacient_id}/consultatii/{consultatie_id}")
def get_consultatie_detaliu(pacient_id: int, consultatie_id: int, db: Session = Depends(get_db)):
    c = (
        db.query(Consultatie)
        .filter(Consultatie.id == consultatie_id, Consultatie.pacient_id == pacient_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Consultatia nu exista")

    def decode(text):
        return gdpr.decrypt(text) if text else ""

    return {
        "id": c.id,
        "data_consultatiei": str(c.data_consultatiei),
        "transcript": decode(c.transcript_audio),
        "diagnostic_ai": decode(c.rezumat_diagnostic),
        "corectie_medic": decode(c.raport_corectat_medic),
        "sugestii": c.sugestii_tratament or "",
        "are_corectie": bool(c.raport_corectat_medic),
        "utilizat_fl": bool(c.utilizat_pentru_fl),
    }
