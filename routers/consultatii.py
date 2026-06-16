from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db, Consultatie
from schemas.consultatie import CorectieMedic
from services.gdpr_service import gdpr

router = APIRouter(tags=["Consultatii"])


@router.put("/consultatii/{consultatie_id}/corectie")
def salveaza_corectia_medicului(
    consultatie_id: int, corectie: CorectieMedic, db: Session = Depends(get_db)
):
    consultatie = db.query(Consultatie).filter(Consultatie.id == consultatie_id).first()
    if not consultatie:
        raise HTTPException(status_code=404, detail="Consultatia nu a fost gasita")

    consultatie.raport_corectat_medic = gdpr.encrypt(corectie.text_corectat)
    consultatie.utilizat_pentru_fl = 0
    db.commit()
    gdpr.log_access("CORRECTION_SAVED", "medic", f"Corectie consultatie ID {consultatie_id}")
    return {"message": "Corectura salvata, criptata si marcata pentru Federated Learning!"}
