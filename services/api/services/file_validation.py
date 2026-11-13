# services/api/services/file_validation.py
# Este archivo contiene las funciones para validar los archivos subidos por el usuario

from pathlib import Path    #Path es una clase que permite trabajar con rutas de archivos
from typing import Any    #Any es un tipo de dato que permite cualquier tipo de dato

import yaml    #yaml es un modulo que permite trabajar con archivos YAML


MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB es el tamaño maximo permitido para los archivos


def _validate_file_size(content: bytes) -> None:
    """Comprueba que el archivo no esté vacío ni supere el tamaño permitido."""

    if not content:
        raise ValueError("The uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("The uploaded file exceeds the 5 MB limit.")


def _validate_extension(filename: str, allowed_extensions: set[str]) -> None:   # allowed_extensions: set[str] es un conjunto de extensiones permitidas, set[str] es un conjunto de strings
    """Comprueba que el archivo tenga una extensión permitida."""

    extension = Path(filename).suffix.lower()    # Path(filename).suffix.lower() es la extension del archivo en minusculas

    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))    # sorted(allowed_extensions) es un conjunto de extensiones permitidas ordenadas alfabeticamente
        raise ValueError(f"Invalid file extension. Allowed extensions: {allowed}")


def validate_markdown_file(filename: str, content: bytes) -> str:   
    """Valida un archivo Markdown y devuelve su contenido como texto."""

    _validate_extension(filename, {".md"})
    _validate_file_size(content)

    try:
        markdown_content = content.decode("utf-8")   # content.decode("utf-8") es el contenido del archivo en utf-8
    except UnicodeDecodeError as exc:
        raise ValueError("The Markdown file must use UTF-8 encoding.") from exc

    if not markdown_content.strip():
        raise ValueError("The Markdown file does not contain readable text.")   # markdown_content.strip() es el contenido del archivo sin espacios en blanco

    if "\x00" in markdown_content:
        raise ValueError("The Markdown file contains invalid binary data.")   # "\x00" es un caracter invalido en el archivo

    return markdown_content


def validate_openapi_file(filename: str, content: bytes) -> dict[str, Any]:
    """Valida una especificación OpenAPI JSON o YAML."""

    _validate_extension(filename, {".json", ".yaml", ".yml"})
    _validate_file_size(content)

    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("The OpenAPI file must use UTF-8 encoding.") from exc

    try:
        specification = yaml.safe_load(text_content)
    except yaml.YAMLError as exc:
        raise ValueError("The OpenAPI file contains invalid JSON or YAML.") from exc

    if not isinstance(specification, dict):
        raise ValueError("The OpenAPI specification must be a JSON or YAML object.")

    version = specification.get("openapi")

    if not isinstance(version, str) or not (
        version.startswith("3.0.") or version.startswith("3.1.")
    ):
        raise ValueError("Only OpenAPI versions 3.0.x and 3.1.x are supported.")

    if not isinstance(specification.get("info"), dict):
        raise ValueError("The OpenAPI specification must contain an info object.")

    if not isinstance(specification.get("paths"), dict):
        raise ValueError("The OpenAPI specification must contain a paths object.")

    return specification