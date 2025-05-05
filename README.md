# Navigation Server

Серверная часть клиент-серверного приложения для внутренней навигации и построения динамической карты здания.

## Требования

- Python ≥3.9  
- PostgreSQL ≥12  
- `asyncpg`  
- FastAPI  
- SQLAlchemy (async)  
- Alembic  
- Uvicorn  

## Установка

1. Клонировать репозиторий:
   git clone https://github.com/mixan193/navigation_server.git
   cd navigation_server
Создать и активировать виртуальное окружение:

python -m venv venv
source venv/bin/activate
Установить зависимости:

pip install -r requirements.txt
Скопировать файл окружения и внести настройки:

cp .env.example .env
# или просто создать .env по образцу
Настройка базы данных и миграции
Обновите DATABASE_URL в файле .env.

Запустите миграции Alembic:

alembic upgrade head
Запуск сервера
bash
Копировать
Редактировать
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
API будет доступен по адресу http://localhost:8000/v1.

Тестирование
Установите дополнительные зависимости для тестов (если есть):

pip install pytest pytest-asyncio httpx
Запустите:

bash
Копировать
Редактировать
pytest
yaml
Копировать
Редактировать

---

**`app/api/routers/__init__.py`**

```python
# Пакет роутеров API
from . import health, upload, map, ap