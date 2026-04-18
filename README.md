# consorcio-autogestionado-back

Backend de la aplicación Consorcio Autogestionado. Desarrollado con Python + FastAPI + Supabase.

## Stack

- Python 3.11 + FastAPI
- Poetry (gestión de dependencias)
- Supabase (base de datos PostgreSQL + storage)
- python-jose (JWT)
- passlib/bcrypt (hash de contraseñas)
- Loguru (logging)
- Docker + Docker Compose

## Setup local

```bash
cp .env.example .env
# Completar JWT_SECRET y DATABASE_URL como mínimo

make install
make dev
# API disponible en http://localhost:8000
```

## Con Docker (local)

```bash
make up-local
# API disponible en http://localhost:8001
# Postgres disponible en localhost:5432
```

## Con Supabase (remoto)

```bash
# Completar .env con SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, DATABASE_URL
make up-remote
```

## Variables de entorno

| Variable | Descripción |
|---|---|
| `JWT_SECRET` | Clave secreta para firmar tokens JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL del access token (default: 60) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | TTL del refresh token (default: 30) |
| `DATABASE_URL` | Connection string PostgreSQL |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_KEY` | Anon key de Supabase |
| `SUPABASE_SERVICE_KEY` | Service role key (para operaciones de storage) |

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET | `/health/db` | Conectividad con la base de datos |
| POST | `/auth/register` | Registro de usuario |
| POST | `/auth/login` | Login |
| POST | `/auth/refresh` | Renovar access token |
| POST | `/auth/logout` | Logout |
| GET | `/users/me` | Perfil propio (JWT requerido) |
| PATCH | `/users/me` | Actualizar perfil |
| POST | `/users/me/avatar` | Subir avatar |
| GET | `/users/{id}/profile` | Perfil público |

## Migraciones

Las migraciones se gestionan con Supabase CLI y se almacenan en `supabase/migrations/`.

```bash
make migrate   # supabase db push
```

## Estructura

```
src/
  main.py            # Entrada FastAPI
  core/
    config.py        # Settings (pydantic-settings)
    security.py      # JWT + bcrypt
    logger.py        # Loguru
  database/
    supabase_client.py  # Cliente Supabase
  routers/           # Endpoints HTTP
  schemas/           # Pydantic v2 schemas (request/response)
  models/            # Modelos de datos
  services/          # Lógica de negocio
  repositories/      # Acceso a datos
supabase/
  migrations/        # SQL migrations
```
