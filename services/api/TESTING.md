# Testing de la API

Las pruebas de upload usan una base de datos independiente: `repolens_test`.

## Variables de entorno

En `services/api/.env`:

```env
DATABASE_URL=postgresql+psycopg://repolens:local_dev_only_change_me@localhost:5433/repolens
TEST_DATABASE_URL=postgresql+psycopg://repolens:local_dev_only_change_me@localhost:5433/repolens_test
```

- Desarrollo usa `DATABASE_URL`.
- Las pruebas usan únicamente `TEST_DATABASE_URL`.
- Si `TEST_DATABASE_URL` no está definida, o coincide con `DATABASE_URL`, las pruebas fallan sin tocar la base de desarrollo.

## Crear la base de testing

Con el contenedor PostgreSQL en marcha (`docker compose up -d db`):

```powershell
docker exec -it repolens-db psql -U repolens -d postgres -c "CREATE DATABASE repolens_test;"
```

Si la base ya existe, PostgreSQL devolverá un error inofensivo.

## Aplicar migraciones a la base de testing

Desde `services/api`, apuntá Alembic temporalmente a la base de test:

```powershell
cd services/api
$env:DATABASE_URL = "postgresql+psycopg://repolens:local_dev_only_change_me@localhost:5433/repolens_test"
.\.venv\Scripts\alembic.exe upgrade head
```

Esto reutiliza las migraciones existentes; no crea migraciones nuevas.

Importante: no dejes `DATABASE_URL` apuntando a `repolens_test` en la sesión de desarrollo. Volvé a cargar el `.env` o reabrí la terminal.

## Ejecutar las pruebas

```powershell
cd services/api
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe test\test_upload.py
```

Las pruebas limpian registros y archivos creados incluso si una aserción falla.
