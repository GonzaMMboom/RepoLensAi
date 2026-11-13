"""Pruebas del endpoint POST /analyses/upload y rutas relacionadas."""

from __future__ import annotations

import os
from io import BytesIO
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set. Configure a dedicated test database "
        "(repolens_test) before running these tests. "
        "Tests will not run against DATABASE_URL."
    )

if DATABASE_URL and TEST_DATABASE_URL == DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must be different from DATABASE_URL "
        "to avoid running tests against the development database."
    )

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

from database import get_db
from main import app
from models.analysis import Analysis
from services.file_storage import (
    MARKDOWN_INTERNAL_NAME,
    delete_analysis_files,
    get_analysis_upload_dir,
    openapi_internal_filename,
)


def get_test_db():
    """Sesión de base de datos apuntando únicamente a TEST_DATABASE_URL."""

    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_db] = get_test_db

VALID_MARKDOWN = b"# RepoLens AI\n\nProject documentation.\n"

VALID_OPENAPI = b"""{
  "openapi": "3.0.3",
  "info": {
    "title": "Test API",
    "version": "1.0.0"
  },
  "paths": {
    "/users": {
      "get": {
        "responses": {
          "200": {
            "description": "Successful response"
          }
        }
      }
    }
  }
}
"""

INVALID_OPENAPI = b"""{
  "openapi": "2.0",
  "info": {
    "title": "Legacy API",
    "version": "1.0.0"
  },
  "paths": {}
}
"""


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _track_created_id(created_ids: list[UUID], analysis_id: UUID) -> None:
    if analysis_id not in created_ids:
        created_ids.append(analysis_id)


def _cleanup_analysis(analysis_id: UUID) -> None:
    delete_analysis_files(analysis_id)

    with Session(test_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        if analysis is not None:
            session.delete(analysis)
            session.commit()


def _cleanup_tracked(created_ids: list[UUID]) -> None:
    for analysis_id in list(created_ids):
        _cleanup_analysis(analysis_id)
        leftover = get_analysis_upload_dir(analysis_id)
        _assert(
            not leftover.exists(),
            f"Upload directory should be cleaned up after tests: {leftover}",
        )


def _upload(
    client: TestClient,
    markdown_filename: str,
    markdown_content: bytes,
    openapi_filename: str,
    openapi_content: bytes,
):
    return client.post(
        "/analyses/upload",
        files={
            "markdown_file": (
                markdown_filename,
                BytesIO(markdown_content),
                "text/markdown",
            ),
            "openapi_file": (
                openapi_filename,
                BytesIO(openapi_content),
                "application/json",
            ),
        },
    )


def test_successful_upload(client: TestClient, created_ids: list[UUID]) -> UUID:
    print("1. Subida exitosa de ambos archivos")

    response = _upload(
        client,
        "docs/my-guide.md",
        VALID_MARKDOWN,
        "specs/api.json",
        VALID_OPENAPI,
    )

    if response.status_code == 201:
        _track_created_id(created_ids, UUID(response.json()["id"]))

    _assert(response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}")

    payload = response.json()
    analysis_id = UUID(payload["id"])

    _assert(payload["status"] == "pending", f"Expected status pending, got {payload['status']}")
    _assert(
        payload["markdown_filename"] == "my-guide.md",
        "Original markdown filename should be basename only",
    )
    _assert(
        payload["openapi_filename"] == "api.json",
        "Original openapi filename should be basename only",
    )

    with Session(test_engine) as session:
        analysis = session.scalar(select(Analysis).where(Analysis.id == analysis_id))
        _assert(analysis is not None, "Analysis was not persisted in PostgreSQL")
        _assert(analysis.status == "pending", "Persisted analysis should be pending")
        _assert(analysis.markdown_filename == "my-guide.md", "Wrong persisted markdown filename")
        _assert(analysis.openapi_filename == "api.json", "Wrong persisted openapi filename")

    upload_dir = get_analysis_upload_dir(analysis_id)
    markdown_path = upload_dir / MARKDOWN_INTERNAL_NAME
    openapi_path = upload_dir / openapi_internal_filename("api.json")

    _assert(upload_dir.is_dir(), "Upload directory was not created")
    _assert(markdown_path.is_file(), "documentation.md was not stored")
    _assert(openapi_path.is_file(), "openapi.json was not stored")
    _assert(markdown_path.read_bytes() == VALID_MARKDOWN, "Stored markdown content mismatch")
    _assert(openapi_path.read_bytes() == VALID_OPENAPI, "Stored openapi content mismatch")

    print("   OK — registro persistido y archivos almacenados")
    return analysis_id


def test_invalid_extension(client: TestClient) -> None:
    print("2. Rechazo de extensiones inválidas")

    response = _upload(
        client,
        "document.txt",
        VALID_MARKDOWN,
        "openapi.json",
        VALID_OPENAPI,
    )

    _assert(response.status_code == 400, f"Expected 400, got {response.status_code}")
    _assert("extension" in response.json()["detail"].lower(), "Expected extension error detail")
    print("   OK — extensión inválida rechazada")


def test_empty_file(client: TestClient) -> None:
    print("3. Rechazo de archivos vacíos")

    response = _upload(
        client,
        "documentation.md",
        b"",
        "openapi.json",
        VALID_OPENAPI,
    )

    _assert(response.status_code == 400, f"Expected 400, got {response.status_code}")
    _assert("empty" in response.json()["detail"].lower(), "Expected empty file error detail")
    print("   OK — archivo vacío rechazado")


def test_invalid_openapi(client: TestClient) -> None:
    print("4. Rechazo de OpenAPI inválido")

    response = _upload(
        client,
        "documentation.md",
        VALID_MARKDOWN,
        "openapi.json",
        INVALID_OPENAPI,
    )

    _assert(response.status_code == 400, f"Expected 400, got {response.status_code}")
    _assert("openapi" in response.json()["detail"].lower(), "Expected OpenAPI version error")
    print("   OK — OpenAPI inválido rechazado")


def test_file_too_large(client: TestClient) -> None:
    print("5. Rechazo de archivos que superan 5 MB")

    oversized = b"#" + (b"a" * (5 * 1024 * 1024))
    response = _upload(
        client,
        "documentation.md",
        oversized,
        "openapi.json",
        VALID_OPENAPI,
    )

    _assert(response.status_code == 400, f"Expected 400, got {response.status_code}")
    _assert("5 mb" in response.json()["detail"].lower(), "Expected size limit error detail")
    print("   OK — archivo oversized rechazado")


def test_existing_routes_404(client: TestClient) -> None:
    print("6. Respuesta 404 de rutas existentes")

    missing_id = uuid4()

    get_response = client.get(f"/analyses/{missing_id}")
    delete_response = client.delete(f"/analyses/{missing_id}")

    _assert(get_response.status_code == 404, f"Expected GET 404, got {get_response.status_code}")
    _assert(
        delete_response.status_code == 404,
        f"Expected DELETE 404, got {delete_response.status_code}",
    )
    print("   OK — GET/DELETE inexistentes responden 404")


def test_delete_removes_physical_files(client: TestClient, created_ids: list[UUID]) -> None:
    print("7. DELETE elimina también los archivos físicos")

    response = _upload(
        client,
        "documentation.md",
        VALID_MARKDOWN,
        "openapi.json",
        VALID_OPENAPI,
    )

    if response.status_code == 201:
        _track_created_id(created_ids, UUID(response.json()["id"]))

    _assert(response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}")

    analysis_id = UUID(response.json()["id"])
    upload_dir = get_analysis_upload_dir(analysis_id)
    _assert(upload_dir.is_dir(), "Upload directory should exist before DELETE")

    delete_response = client.delete(f"/analyses/{analysis_id}")
    _assert(
        delete_response.status_code == 204,
        f"Expected DELETE 204, got {delete_response.status_code}: {delete_response.text}",
    )

    with Session(test_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        _assert(analysis is None, "Analysis should be removed from PostgreSQL")

    _assert(not upload_dir.exists(), "Upload directory should be removed after DELETE")

    if analysis_id in created_ids:
        created_ids.remove(analysis_id)

    print("   OK — DELETE eliminó registro y archivos físicos")


def main() -> None:
    created_ids: list[UUID] = []

    with TestClient(app) as client:
        try:
            test_successful_upload(client, created_ids)
            test_invalid_extension(client)
            test_empty_file(client)
            test_invalid_openapi(client)
            test_file_too_large(client)
            test_existing_routes_404(client)
            test_delete_removes_physical_files(client, created_ids)
            print("\nAll upload tests passed.")
        finally:
            _cleanup_tracked(created_ids)
            app.dependency_overrides.clear()


if __name__ == "__main__":
    main()
