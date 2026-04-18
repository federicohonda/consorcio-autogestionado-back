# consorcio-autogestionado-back

Backend de la aplicación **Consorcio Autogestionado** (GDSI TP4). API REST desarrollada con Python + FastAPI, base de datos PostgreSQL, sin ORM (SQL puro con psycopg2). Migraciones automáticas al arrancar el contenedor.

---

## Stack

| Tecnología | Versión / Uso |
|---|---|
| Python | 3.11 |
| FastAPI | Framework HTTP |
| Poetry | Gestión de dependencias |
| psycopg2-binary | Driver PostgreSQL (SQL puro, sin ORM) |
| python-jose | Generación y validación de JWT |
| bcrypt | Hash de contraseñas (directo, sin passlib) |
| Pydantic v2 | Schemas de request/response con alias camelCase |
| Loguru | Logging |
| Docker + Docker Compose | Contenedores local y producción |
| Supabase | PostgreSQL en producción |
| Railway | Hosting del contenedor Docker en producción |

---

## Estructura del proyecto

```
consorcio-autogestionado-back/
├── src/
│   ├── main.py                   # Entrada FastAPI, registro de routers
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings, lee .env)
│   │   ├── security.py           # JWT (crear/verificar tokens), bcrypt
│   │   └── logger.py             # Configuración Loguru
│   ├── database/
│   │   ├── connection.py         # get_db_cursor() — context manager psycopg2
│   │   └── migrate.py            # Auto-migración: lee y ejecuta supabase/migrations/*.sql
│   ├── routers/
│   │   ├── health.py             # GET /health, GET /health/db
│   │   ├── auth.py               # POST /auth/register, /login, /refresh, /logout
│   │   ├── users.py              # GET/PATCH /users/me, GET /users/{id}/profile
│   │   └── groups.py             # Grupos, miembros y gastos (11 endpoints)
│   ├── schemas/
│   │   ├── auth.py               # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── user.py               # UserResponse, UpdateProfileRequest
│   │   ├── group.py              # CreateGroupRequest, GroupResponse, MemberResponse, TransferRoleRequest
│   │   └── expense.py            # CreateExpenseRequest, ExpenseResponse, MonthlySummaryResponse
│   ├── models/
│   │   ├── user.py               # User dataclass
│   │   ├── group.py              # Group, GroupMember, GroupMemberWithUser dataclasses
│   │   └── expense.py            # Expense, ExpenseSplit, ExpenseWithSplits dataclasses
│   ├── services/
│   │   ├── auth_service.py       # register, login, refresh_token, logout
│   │   ├── user_service.py       # get_me, update_profile
│   │   ├── group_service.py      # create_group, join_group, transfer_admin, leave_group
│   │   └── expense_service.py    # create_expense (divide en partes iguales)
│   └── repositories/
│       ├── user_repository.py    # CRUD usuarios
│       ├── group_repository.py   # CRUD grupos y miembros
│       └── expense_repository.py # CRUD gastos, splits, resumen mensual
├── supabase/
│   └── migrations/
│       ├── 20260418000000_create_users.sql
│       ├── 20260418000001_create_groups.sql
│       └── 20260418000002_create_expenses.sql
├── Makefile
├── Dockerfile
├── docker-compose.local.yml
├── docker-compose.remote.yml
├── pyproject.toml
└── .env.example
```

---

## Variables de entorno

Copiá `.env.example` a `.env` y completá los valores:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | Connection string PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET` | Clave secreta para firmar tokens JWT | cadena larga aleatoria |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL del access token | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | TTL del refresh token | `30` |

> Las variables `SUPABASE_URL`, `SUPABASE_KEY` y `SUPABASE_SERVICE_KEY` fueron parte de una versión anterior con el cliente Supabase Python. La versión actual usa psycopg2 directamente — solo `DATABASE_URL` es necesaria.

---

## Ejecución local

### Opción A — Docker Compose con Postgres local (recomendado)

```bash
cp .env.example .env
# Completar JWT_SECRET y DATABASE_URL (puede ser postgresql://postgres:postgres@db:5432/consorcio)

make up-local
# API disponible en http://localhost:8001
# Postgres disponible en localhost:5432
```

Las migraciones se ejecutan automáticamente al iniciar el contenedor (`src/database/migrate.py`).

### Opción B — Directo con Poetry (requiere Postgres externo)

```bash
cp .env.example .env
# Completar DATABASE_URL apuntando a tu Postgres

poetry install
poetry run uvicorn src.main:app --reload --port 8000
# API disponible en http://localhost:8000
```

### Comandos útiles

```bash
make up-local      # Levanta API + Postgres en Docker
make down          # Baja los contenedores
make logs          # Logs del contenedor de la API
make install       # poetry install
make dev           # uvicorn --reload (sin Docker)
```

---

## Sistema de migraciones

Las migraciones viven en `supabase/migrations/` como archivos `.sql` nombrados con timestamp (`YYYYMMDDHHMMSS_nombre.sql`). Al arrancar el contenedor, `src/database/migrate.py`:

1. Lee todos los archivos `.sql` ordenados por nombre.
2. Ejecuta cada uno contra la base de datos.
3. Todos los archivos usan `CREATE TABLE IF NOT EXISTS` e índices con `IF NOT EXISTS`, por lo que son idempotentes.

No hay herramienta externa de migraciones (ni Alembic ni Supabase CLI) — el proceso es completamente autónomo.

**Tablas creadas:**

| Tabla | Descripción |
|---|---|
| `users` | Usuarios registrados (email, full_name, password_hash, refresh_token) |
| `groups` | Grupos/consorcios (name, description, icon) |
| `group_members` | Relación N:M users↔groups con rol (Administrador / Miembro) |
| `expenses` | Gastos registrados por grupo |
| `expense_splits` | División del gasto por usuario (partes iguales) |

---

## Endpoints

### Health

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/health` | No | Estado del servicio |
| GET | `/health/db` | No | Conectividad con la base de datos |

### Auth

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/register` | No | Registro de usuario |
| POST | `/auth/login` | No | Login, devuelve access + refresh token |
| POST | `/auth/refresh` | No | Renueva access token con refresh token |
| POST | `/auth/logout` | JWT | Invalida refresh token |

### Users

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/users/me` | JWT | Perfil del usuario autenticado |
| PATCH | `/users/me` | JWT | Actualizar nombre o email |
| GET | `/users/{id}/profile` | JWT | Perfil público de otro usuario |

### Groups

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/groups` | JWT | Crear grupo (creador → Administrador) |
| GET | `/groups` | JWT | Listar todos los grupos |
| GET | `/groups/mine` | JWT | Grupo actual del usuario (404 si no tiene) |
| POST | `/groups/{id}/join` | JWT | Unirse al grupo (un usuario → un grupo a la vez) |
| GET | `/groups/{id}/members` | JWT | Listar miembros con rol |
| PATCH | `/groups/{id}/transfer-admin` | JWT | Transferir rol Administrador (solo el admin actual) |
| POST | `/groups/{id}/leave` | JWT | Salir del grupo (bloqueado si hay deuda pendiente) |

### Expenses

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/groups/{id}/expenses` | JWT | Registrar gasto (se divide en partes iguales) |
| GET | `/groups/{id}/expenses` | JWT | Listar gastos del mes (`?year=&month=`) |
| GET | `/groups/{id}/summary` | JWT | Resumen mensual: total + balance personal |

---

## Decisiones de diseño relevantes

- **Sin ORM**: todas las queries son SQL puro con psycopg2 y `RealDictCursor`. Permite control total sobre las queries y no introduce magia implícita.
- **bcrypt directo**: `passlib` fue removido por incompatibilidad con `bcrypt>=4.x`. Se usa `bcrypt.hashpw` / `bcrypt.checkpw` directamente.
- **Pydantic v2 con alias**: los schemas usan `model_config = ConfigDict(populate_by_name=True)` y campos con `alias` camelCase para la API pública, manteniendo snake_case internamente.
- **Imports con `import ... as`**: se usa `import src.repositories.group_repository as group_repository` en lugar de `from src.repositories import ...` para evitar conflictos con el sistema de módulos de Python.
- **Exclusividad de grupo**: un usuario solo puede pertenecer a un grupo a la vez. La restricción se aplica en `join_group` consultando `get_user_group(user_id)` antes de insertar.
- **Restricción de salida**: `leave_group` bloquea si el balance histórico del usuario es negativo (debe dinero al grupo). Calcula `SUM(pagado) - SUM(parte_asignada)` sobre todos los gastos del grupo.

---

## Deploy en Railway + Supabase

### Base de datos (Supabase)

1. Crear proyecto en [supabase.com](https://supabase.com).
2. Ir al botón **Connect** (parte superior del dashboard).
3. Copiar la URI de **Session pooler** (puerto 5432, modo `?pgbouncer=true` desactivado si corresponde).
4. Usar esa URI como `DATABASE_URL` en Railway.

### API (Railway)

1. Crear proyecto en [railway.app](https://railway.app) y conectar el repositorio.
2. Railway detecta el `Dockerfile` automáticamente.
3. En **Variables**, configurar:
   - `DATABASE_URL` — URI del Session pooler de Supabase
   - `JWT_SECRET` — cadena secreta larga
   - `ACCESS_TOKEN_EXPIRE_MINUTES` — `60`
   - `REFRESH_TOKEN_EXPIRE_DAYS` — `30`
4. Al deployar, el contenedor arranca, ejecuta las migraciones y expone el puerto configurado.
5. Copiar la URL pública de Railway (ej: `https://consorcio-back-production.up.railway.app`) para usarla como `EXPO_PUBLIC_API_URL` en el frontend.

### Deployar cambios nuevos

Railway redeploya automáticamente con cada push a la rama conectada:

```bash
git add .
git commit -m "descripción del cambio"
git push
```

Railway detecta el push, reconstruye la imagen Docker y reemplaza el contenedor. Las migraciones nuevas (si las hay) se ejecutan automáticamente al iniciar el nuevo contenedor.

> Si agregás una migración nueva, simplemente creá el archivo `.sql` en `supabase/migrations/` con un timestamp mayor al último. El sistema la ejecutará sola al deployar.

---

## Historias de usuario

### Completadas

| HU | Épica | Historia | Notas de implementación |
|---|---|---|---|
| HU-02 | Ingreso y contexto del grupo | Acceso al grupo — ingresar al grupo compartido para ver la información principal | `GET /groups/mine`, `POST /groups/{id}/join`, selección y creación de grupo |
| HU-03 | Pantalla principal | Resumen general del mes — ver cuánto se gastó y cuál es la situación del socio | `GET /groups/{id}/summary` devuelve total_expenses + your_balance |
| HU-06 | Pantalla principal | Últimos gastos registrados — ver los últimos gastos cargados | `GET /groups/{id}/expenses` con filtro por año/mes |
| HU-07 | Gestión de gastos | Registro manual de un gasto común — cargar un gasto para que quede registrado | `POST /groups/{id}/expenses` |
| HU-09 | Gestión de gastos | Ingreso de descripción y monto — identificar el gasto con descripción y monto | Campos `description` y `amount` en `CreateExpenseRequest` |
| HU-10 | Gestión de gastos | Identificación de quién pagó el gasto — indicar el pagador para calcular aportes y recuperos | Campo `paid_by_user_id` en request; `paid_by_name` en response |
| HU-11 | Gestión de gastos | División del gasto en partes iguales — repartir el gasto entre todos los integrantes | `expense_service.py` divide `amount / len(members)` y crea `expense_splits` |
| HU-18 | Balance y reportes | Balance mensual individual — cuánto gasté, cuánto me corresponde y mi diferencia final | `your_balance = you_paid - your_share` en summary |
| HU-22 | Balance y reportes | Claridad visual del saldo y las diferencias — visualización clara de cuánto debo o cobro | Balance devuelto con signo: positivo = recupera, negativo = debe |

### Funcionalidades extra implementadas (fuera del backlog)

| Feature | Descripción |
|---|---|
| Crear grupo con icono | `POST /groups` acepta name, description e icon (preset de íconos Ionicons) |
| Listar grupos disponibles | `GET /groups` permite ver todos los grupos disponibles para unirse |
| Exclusividad de grupo | Un usuario solo puede pertenecer a un grupo a la vez; validado en `join_group` |
| Ver miembros con roles | `GET /groups/{id}/members` devuelve lista con rol (Administrador / Miembro) |
| Transferir rol de Administrador | `PATCH /groups/{id}/transfer-admin` con validación de que el solicitante sea admin |
| Salir de un grupo | `POST /groups/{id}/leave` bloqueado si el balance histórico del usuario es negativo |
| Refresh token automático | `POST /auth/refresh`; el frontend lo invoca automáticamente mediante interceptor Axios |
| Migraciones automáticas | `src/database/migrate.py` ejecuta los `.sql` de `supabase/migrations/` al iniciar el contenedor, sin CLI externo |

### Pendientes

| HU | Épica | Historia |
|---|---|---|
| HU-01 | Ingreso y contexto del grupo | Selección del tipo de grupo al ingresar para adaptar la experiencia al contexto del consorcio |
| HU-04 | Pantalla principal | Accesos rápidos a acciones clave: cargar gasto, pagar, ver balance y reportes |
| HU-05 | Pantalla principal | Visualización de alertas relevantes sobre deuda o mora |
| HU-08 | Gestión de gastos | Selección de categoría del gasto para ordenar los movimientos |
| HU-12 | Gestión de gastos | División proporcional del gasto (no en partes iguales) |
| HU-13 | Gestión de gastos | Adjuntar comprobante o imagen al registrar un gasto |
| HU-14 | Gestión de gastos | Registrar gastos recurrentes para no cargarlos manualmente cada mes |
| HU-15 | Gestión de gastos | Registro de pago de expensas o saldo para actualizar deuda pendiente |
| HU-16 | Gestión de gastos | Adjuntar comprobante al pago |
| HU-17 | Gestión de gastos | Pago a un fondo común centralizado |
| HU-19 | Balance y reportes | Balance general de todos los socios — quién debe y quién cobra |
| HU-20 | Balance y reportes | Reporte de estado de cuentas del período |
| HU-21 | Balance y reportes | Detalle de gastos dentro del reporte de estado de cuentas |
| HU-23 | Socios y mora | Listado de socios con su situación actual (saldo, deuda) |
| HU-24 | Socios y mora | Identificación de socios en mora para hacer seguimiento de deudas vencidas |
