from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import check_db_connection
from routers.analyses import router as analyses_router

app = FastAPI(
    title="RepoLens AI API",
    description="API para analizar documentación y detectar inconsistencias",
    version="0.1.0",

)

# permite que el frontend acceda a la API
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.0.20:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],  # Permitir todos los métodos HTTP
    allow_headers=["*"],  # Permitir todos los encabezados
)

app.include_router(analyses_router)

@app.get("/health")
def health_check():
    return {"status":"OK"}

@app.get("/health/db")
def health_db():
    try:
        check_db_connection()
        return {"status":"OK"}
    except Exception:
        raise HTTPException(status_code=500, detail="database connection failed")