from fastapi import FastAPI

app = FastAPI(
    title="RepoLens AI API",
    description="API para analizar documentación y detectar inconsistencias",
    version="0.1.0",

)

@app.get("/")
def health_check():
    return {"status":"OK"}
