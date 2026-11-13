from services.file_validation import validate_markdown_file, validate_openapi_file



# 1. Probar Markdown
markdown = b"# RepoLens AI\n\nProject documentation."

result = validate_markdown_file(
    "documentation.md",
    markdown,
)

print("Markdown validated:", result[:20])   # result[:20] es el contenido del archivo hasta 20 caracteres


# 2. Probar OpenAPI JSON
openapi = b"""
{
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

specification = validate_openapi_file(
    "openapi.json",
    openapi,
)

print("OpenAPI version:", specification["openapi"])
print("Available paths:", list(specification["paths"].keys()))


# 3. Probar una extensión inválida
try:
    validate_markdown_file("document.txt", markdown)
except ValueError as error:
    print("Invalid extension detected:", error)