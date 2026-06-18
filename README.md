# Booking Service

Асинхронный бэкенд-сервис для записи на встречи с фоновой обработкой задач.

[![CI](https://github.com/your-username/booking-service/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/booking-service/actions/workflows/ci.yml)

## Стек технологий

| Слой | Технология |
|---|---|
| API-фреймворк | FastAPI 0.115 |
| Очередь задач | TaskIQ + Redis broker |
| База данных | PostgreSQL 16 + SQLAlchemy 2.0 (async) |
| Миграции | Alembic |
| Логирование | structlog (JSON в продакшне) |
| Rate Limiting | slowapi |
| Тесты | pytest + httpx + aiosqlite |
| Линтер | ruff + mypy (strict) |

---

## Быстрый старт

### Требования

- Docker и Docker Compose

### Запуск

```bash
cp .env.example .env
docker-compose up --build
```

Одна команда запускает:
1. PostgreSQL и Redis
2. Alembic-миграции
3. FastAPI-сервер на `http://localhost:8000`
4. TaskIQ-воркер для фоновой обработки

### Проверка

```bash
curl http://localhost:8000/health
# {"status":"ok","env":"development"}
```

Swagger UI: http://localhost:8000/docs

---

## Разработка без пересборки

При работе над кодом используй отдельный dev-конфиг — код монтируется как volume, пересборка образа не нужна:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

После этого любое изменение в `src/` применяется автоматически. Пересборка нужна только при изменении `requirements.txt` или `Dockerfile`.

---

## API

### Создать бронь
```bash
curl -X POST http://localhost:8000/api/v1/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Петров",
    "scheduled_at": "2099-06-01T10:00:00+03:00",
    "service_type": "consultation"
  }'
```

Доступные значения `service_type`: `consultation`, `repair`, `installation`, `maintenance`, `inspection`

### Получить статус брони
```bash
curl http://localhost:8000/api/v1/bookings/{id}
```

Возможные статусы: `pending` → `confirmed` / `failed` / `cancelled`

### Список броней
```bash
curl "http://localhost:8000/api/v1/bookings?status=pending&page=1&size=20"
```

### Отменить бронь
```bash
curl -X DELETE http://localhost:8000/api/v1/bookings/{id}
```

> Отменить можно только бронь в статусе `pending`. При другом статусе — `409 Conflict`.

---

## Запуск тестов

### Вариант 1 — Docker (рекомендуется для CI)

```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

### Вариант 2 — Локально без Docker

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements-dev.txt
pytest
```

> Тесты используют SQLite in-memory и мокают TaskIQ — никакой инфраструктуры не нужно.

---

## Команды Makefile