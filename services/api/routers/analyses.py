from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status   #APIRouter para crear un router,que sirve para agrupar endpoints relacionados, Depends para dependencias, HTTPException para manejar errores
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload   #Session para interactuar con la base de datos (select, insert, update, delete) ORM es un concepto que permite mapear objetos a la base de datos

from database import get_db
from models.analysis import Analysis
from schemas.analysis import AnalysisCreate, AnalysisDetailResponse, AnalysisResponse

#prefix es el prefijo de la ruta, tags es el nombre del grupo de endpoints
router = APIRouter(prefix="/analyses", tags=["analyses"])

@router.post("/", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED) #response_model es el modelo de respuesta (lo que nos devuelve la API), status_code es el codigo de estado
def create_analysis(data: AnalysisCreate, db: Session = Depends(get_db)):   #data valida los datos que se envian en la request y además los convierte a los tipos de datos de la base de datos
    """Crea un nuevo analisis"""
    try:
        analysis = Analysis(markdown_filename=data.markdown_filename, openapi_filename=data.openapi_filename)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("", response_model=list[AnalysisResponse])
def get_analyses(db: Session = Depends(get_db)):
        """Obtiene todos los analisis"""
        statements = select(Analysis).order_by(Analysis.created_at.desc())
        analyses = db.scalars(statements).all()  #scalars se usa para obtener los resultados de la consulta como objetos Python
        return analyses

@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailResponse,
)
def get_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
):
    """Obtiene un análisis con sus hallazgos."""

    statement = (
        select(Analysis)
        .options(selectinload(Analysis.findings))
        .where(Analysis.id == analysis_id)
    )

    analysis = db.scalar(statement)

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    return analysis


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
):
    """Elimina un análisis y sus hallazgos."""

    analysis = db.get(Analysis, analysis_id)

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    db.delete(analysis)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)