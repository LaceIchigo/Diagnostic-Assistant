from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from models.database import creaza_tabele
from routers import pacienti, sessions, consultatii, gdpr

app = FastAPI(title="Medical AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

creaza_tabele()

app.include_router(pacienti.router)
app.include_router(sessions.router)
app.include_router(consultatii.router)
app.include_router(gdpr.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
