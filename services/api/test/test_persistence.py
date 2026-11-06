from sqlalchemy import select   #select para seleccionar datos de la base de datos
from sqlalchemy.orm import Session  #Session para interactuar con la base de datos (insertar, consultar, modificar y eliminar registros)    #orm quiere decir object relational mapping, es una manera de mapear objetos a la base de datos

from database import engine  #engine para interactuar con la base de datos
from models import Analysis, Finding  #Analysis y Finding representan las tablas de la base de datos


with Session(engine) as session:  #El with es un administrador de contexto. Se encarga de cerrar la sesión cuando terminamos de trabajar con ella, incluso si ocurre una excepción
    # 1. Crear un análisis
    analysis = Analysis(
        markdown_filename="test-documentation.md",
        openapi_filename="test-openapi.json",
    )

    # 2. Crear un hallazgo asociado
    finding = Finding(
        category="documentation",
        severity="medium",
        title="Endpoint sin documentar",
        description="Se encontró un endpoint en OpenAPI que no aparece en la documentación.",
        evidence="GET /users aparece en OpenAPI, pero no en Markdown.",
        confidence=0.95,
    )

    analysis.findings.append(finding)   #append es un método que agrega un elemento a la lista

    # 3. Guardar ambos registros
    session.add(analysis)
    session.commit()

    print("Análisis guardado:", analysis.id)
    print("Estado:", analysis.status)
    print("Hallazgo guardado:", finding.id)

    # 4. Consultar el análisis y su relación
    saved_analysis = session.scalar(
        select(Analysis).where(Analysis.id == analysis.id)
    )

    print("Hallazgos asociados:", len(saved_analysis.findings))
    print("Título del hallazgo:", saved_analysis.findings[0].title)

    # 5. Eliminar los registros de prueba
    finding_id = finding.id

    session.delete(saved_analysis)
    session.commit()

    deleted_finding = session.scalar(
        select(Finding).where(Finding.id == finding_id)
    )

    print("Hallazgo eliminado:", deleted_finding is None)