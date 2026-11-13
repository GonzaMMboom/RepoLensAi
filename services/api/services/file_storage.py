"""Persistencia de archivos subidos en el filesystem local."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID

UPLOADS_ROOT = Path(__file__).resolve().parent.parent / "storage" / "uploads"

MARKDOWN_INTERNAL_NAME = "documentation.md"


def get_analysis_upload_dir(analysis_id: UUID) -> Path:
    """Devuelve el directorio de almacenamiento de un análisis."""

    return UPLOADS_ROOT / str(analysis_id)


def openapi_internal_filename(original_filename: str) -> str:
    """Genera el nombre interno estable del archivo OpenAPI."""

    extension = Path(original_filename).suffix.lower()
    return f"openapi{extension}"


def save_analysis_files(
    analysis_id: UUID,
    markdown_content: bytes,
    openapi_content: bytes,
    openapi_original_filename: str,
) -> Path:
    """
    Guarda los archivos de un análisis con nombres internos controlados.

    Si falla a mitad de camino, elimina el directorio para evitar archivos huérfanos.
    """

    analysis_dir = get_analysis_upload_dir(analysis_id)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    try:
        markdown_path = analysis_dir / MARKDOWN_INTERNAL_NAME
        openapi_path = analysis_dir / openapi_internal_filename(openapi_original_filename)

        markdown_path.write_bytes(markdown_content)
        openapi_path.write_bytes(openapi_content)
    except Exception:
        delete_analysis_files(analysis_id)
        raise

    return analysis_dir


def delete_analysis_files(analysis_id: UUID) -> None:
    """Elimina el directorio de un análisis si existe.

    Propaga errores de filesystem para que el caller pueda registrarlos.
    """

    analysis_dir = get_analysis_upload_dir(analysis_id)

    if analysis_dir.exists():
        shutil.rmtree(analysis_dir)
