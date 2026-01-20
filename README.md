# Org Directory API

REST API для справочника **Организаций / Зданий / Деятельностей**.

**Стек:** FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · Alembic · PostgreSQL · ORJSON.

## Возможности

- Дерево деятельностей (ограничено **3 уровнями**).
- Организации:
  - получить по `id`
  - список по зданию
  - список по деятельности (по умолчанию **с поддеревом**)
  - поиск по названию (ILIKE)
  - гео-поиск: радиус или bbox
- В Docker-контейнере при старте автоматически:
  1) ожидание готовности Postgres
  2) `alembic upgrade head`
  3) запуск приложения

---

## Быстрый старт (Docker)

1) Создайте `.env`:

```bash
cp .env.example .env
```

2) Отредактируйте `.env` (минимум — `API_KEY`):

```dotenv
API_KEY=change-me
SEED_DATA=true
```

3) Запустите:

```bash
docker compose up --build
```

4) Документация и healthcheck:

- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health` (без API key)

> Если порт `8000` или `5432` занят — поменяйте проброс портов в `docker-compose.yml`.

---

## Аутентификация

Все ручки под `/api/v1/...` защищены статическим API key.

Добавляйте заголовок:

```
X-API-Key: <API_KEY>
```

- Ключ берётся из переменной окружения `API_KEY`.
- При неверном ключе будет `401 Invalid API key`.

> `GET /health` не требует авторизации.

---

## Конфигурация

Основные переменные окружения:

- `API_KEY` — ключ доступа (обязательно сменить на свой)
- `SEED_DATA` — вставлять демо-данные при старте приложения (`true/false`)
- `DATABASE_URL` — строка подключения (нужна при локальном запуске)

Переменные Postgres для docker-compose:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

> Настройки читаются из `.env` (см. `app/core/config.py`). **Не коммитьте `.env` в репозиторий.**

---

## API (v1)

База: `/api/v1`

### Здания

- `GET /buildings` — список зданий

### Организации

- `GET /organizations/{org_id}` — организация по `id`
  - `404 Organization not found`, если не найдена

- `GET /organizations/by-building/{building_id}` — организации в здании

- `GET /organizations/by-activity/{activity_id}` — организации по виду деятельности
  - query: `include_descendants` (bool, **по умолчанию true**) — искать по поддереву

- `GET /organizations/search` — поиск по названию
  - query: `q` (строка, min length = 1)
  - query: `limit` (1..200, default = 50)

- `GET /organizations/geo` — гео-поиск
  - query: `mode` = `radius` | `bbox`
  - mode=radius:
    - `lat`, `lon` — координаты
    - `radius_m` — радиус в метрах (>0)
  - mode=bbox:
    - `min_lat`, `max_lat`, `min_lon`, `max_lon`
  - query: `limit` (1..500, default = 200)
  - при некорректных параметрах вернётся `422` (detail с причиной)

### Деятельности

- `GET /activities/tree` — дерево деятельностей (до 3 уровней)

---

## Примеры запросов

```bash
API_KEY=change-me

curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/buildings
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/organizations/1
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/organizations/by-building/1
curl -H "X-API-Key: $API_KEY" "http://localhost:8000/api/v1/organizations/by-activity/1?include_descendants=true"
curl -H "X-API-Key: $API_KEY" "http://localhost:8000/api/v1/organizations/search?q=Рога&limit=50"
curl -H "X-API-Key: $API_KEY" "http://localhost:8000/api/v1/organizations/geo?mode=radius&lat=55.7558&lon=37.6176&radius_m=5000"
curl -H "X-API-Key: $API_KEY" "http://localhost:8000/api/v1/organizations/geo?mode=bbox&min_lat=55.70&max_lat=55.80&min_lon=37.50&max_lon=37.70"
```

---

## Форматы ответов (кратко)

### Organization

```json
{
  "id": 1,
  "name": "ООО Рога и Копыта",
  "building": {
    "id": 1,
    "address": "г. Москва, ...",
    "latitude": 55.7558,
    "longitude": 37.6176
  },
  "phones": [{"id": 1, "phone": "+7-999-..."}],
  "activities": [{"id": 1, "name": "Еда", "parent_id": null, "level": 1}]
}
```

### Organization + distance

```json
{
  "id": 1,
  "name": "...",
  "building": {"id": 1, "address": "...", "latitude": 0.0, "longitude": 0.0},
  "phones": [],
  "activities": [],
  "distance_m": 123.45
}
```

### Activity tree node

```json
{
  "id": 1,
  "name": "Еда",
  "level": 1,
  "children": [
    {"id": 2, "name": "Мясная продукция", "level": 2, "children": []}
  ]
}
```

---

## Миграции и демо-данные

- При запуске контейнера миграции применяются автоматически: `alembic upgrade head`.
- Демо-данные вставляются при старте приложения (идемпотентно), если `SEED_DATA=true`.

Важно про Docker defaults:
- В `docker-compose.yml` для API стоит `SEED_DATA: ${SEED_DATA:-true}`.
- Если вы **создали `.env`** через `cp .env.example .env`, то будет значение из `.env`.

---

## Локальный запуск (без Docker)

Требуется установленный PostgreSQL и Python 3.12.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt

# пример для локального Postgres
export DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/org_directory'
export API_KEY='change-me'
export SEED_DATA='true'

alembic upgrade head
uvicorn app.main:app --reload
```

Открывайте: `http://localhost:8000/docs`

---

## Тесты

### Вариант 1: Docker

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

### Вариант 2: Локально

```bash
pip install -r requirements-dev.txt
pytest -q
```

> Для локальных тестов нужен Postgres и корректный `DATABASE_URL`.

---

## Полезные команды

Остановить и удалить контейнеры:

```bash
docker compose down
```

Сбросить БД (удалить volume):

```bash
docker compose down -v
```

---

## Структура проекта

- `app/` — FastAPI приложение
  - `api/v1/` — роутеры и эндпоинты
  - `schemas/` — Pydantic-схемы ответов
  - `services/` — запросы к БД
  - `db/` — модели, сессия, seed
  - `core/` — настройки и auth
- `alembic/` — миграции
- `docker/entrypoint.sh` — ожидание БД + миграции + запуск
- `tests/` — тесты

---

## Безопасность

- Не храните реальные ключи и пароли в репозитории.
- `.env` должен быть только локально.
- Используйте длинный случайный `API_KEY` (например 32+ символа).

