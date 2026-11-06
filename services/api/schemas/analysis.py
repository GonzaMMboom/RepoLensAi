from datetime import datetime
from uuid import UUID  #UUID para generar un identificador único

from pydantic import BaseModel, ConfigDict  #BaseModel para definir los modelos de los datos y ConfigDict para configurar el modelo  #Pydantic es un framework para validar datos

class AnalysisCreate(BaseModel):    #BaseModel es la clase de Pydantic que nos permite validar los datos
    """Datos necesarios para crear un analisis"""

    markdown_filename: str
    openapi_filename: str


class FindingResponse(BaseModel):
    """Estructura de respuesta para un hallazgo"""

    model_config = ConfigDict(from_attributes=True) #Permite que Pydantic construya una respuesta a partir de un objeto SQLAlchemy, leyendo directamente sus atributos.
    id: UUID
    analysis_id: UUID
    category: str
    severity: str
    title: str
    description: str
    evidence: str
    confidence: float | None
    created_at: datetime

class AnalysisResponse(BaseModel):
    """Estuctura de respuesta para la API (de un analisis)"""

    model_config = ConfigDict(from_attributes=True) #Permite que Pydantic construya una respuesta a partir de un objeto SQLAlchemy, leyendo directamente sus atributos.
    id: UUID
    status: str
    markdown_filename: str
    openapi_filename: str
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None

class AnalysisDetailResponse(AnalysisResponse):
    """Respuesta de un análisis incluyendo sus hallazgos."""

    findings: list[FindingResponse]