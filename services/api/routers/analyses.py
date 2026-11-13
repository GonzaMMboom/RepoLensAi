import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models.analysis import Analysis
from schemas.analysis import AnalysisCreate, AnalysisDetailResponse, AnalysisResponse
from services.file_storage import (
    delete_analysis_files,
    get_analysis_upload_dir,
    save_analysis_files,
)
from services.file_validation import validate_markdown_file, validate_openapi_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _original_filename(upload: UploadFile) -> str:
    """Obtiene un nombre de archivo seguro (sin rutas) a partir del UploadFile."""

    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Each uploaded file must include a filename.",
        )

    # Evita que nombres como "../../evil.md" se persistan con path traversal.
    return upload.filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]


@router.post("/", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(data: AnalysisCreate, db: Session = Depends(get_db)):
    """Crea un nuevo analisis"""
    try:
        analysis = Analysis(
            markdown_filename=data.markdown_filename,
            openapi_filename=data.openapi_filename,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/upload",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_analysis_documents(
    markdown_file: UploadFile = File(...),
    openapi_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Recibe documentación Markdown y una especificación OpenAPI, las valida y las persiste."""

    markdown_filename = _original_filename(markdown_file)
    openapi_filename = _original_filename(openapi_file)

    markdown_content = markdown_file.file.read()
    openapi_content = openapi_file.file.read()

    try:
        validate_markdown_file(markdown_filename, markdown_content)
        validate_openapi_file(openapi_filename, openapi_content)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    analysis = Analysis(
        markdown_filename=markdown_filename,
        openapi_filename=openapi_filename,
        status="pending",
    )
    db.add(analysis)

    try:
        db.flush()
        save_analysis_files(
            analysis.id,
            markdown_content,
            openapi_content,
            openapi_filename,
        )
        db.commit()
        db.refresh(analysis)
    except Exception as error:
        db.rollback()
        if getattr(analysis, "id", None) is not None:
            try:
                delete_analysis_files(analysis.id)
            except Exception:
                logger.exception(
                    "ORPHAN_UPLOAD_DIR: failed to clean upload directory for analysis %s "
                    "after a failed upload transaction.",
                    analysis.id,
                )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store the uploaded analysis documents.",
        ) from error

    return analysis


@router.get("", response_model=list[AnalysisResponse])
def get_analyses(db: Session = Depends(get_db)):
    """Obtiene todos los analisis"""
    statements = select(Analysis).order_by(Analysis.created_at.desc())
    analyses = db.scalars(statements).all()
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

    try:
        delete_analysis_files(analysis_id)
    except Exception:
        upload_dir = get_analysis_upload_dir(analysis_id)
        logger.exception(
            "ORPHAN_UPLOAD_DIR: analysis %s was deleted from PostgreSQL, "
            "but filesystem cleanup failed for %s. Manual cleanup required.",
            analysis_id,
            upload_dir,
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
