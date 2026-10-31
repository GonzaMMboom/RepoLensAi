from fastapi import FastAPI, HTTPException
from database import check_db_connection

app = FastAPI(
    title="RepoLens AI API",
    description="API para analizar documentación y detectar inconsistencias",
    version="0.1.0",

)

@app.get("/")
def health_check():
    return {"status":"OK"}

@app.get("/health/db")
def health_db():
    try:
        check_db_connection()
        return {"status":"OK"}
    except Exception:
        raise HTTPException(status_code=500, detail="database connection failed")
