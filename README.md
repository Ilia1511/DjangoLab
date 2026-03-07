Quest Aggregator API
Веб-сервис для управления игровыми квестами. Агрегатор позволяет игрокам выполнять квесты в разных играх и получать награды.

Быстрый старт
1. Клонирование и настройка
==============================
git clone <repository-url>
cd WebApp
==============================
2. Создание файла переменных окружения
==============================
cp .env.example .env
==============================
3. Запуск приложения
==============================
docker compose up --build
==============================
4. Файл переменных окружения
==============================
# .env
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=postgres
DB_PORT=5432

SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
===============================
7.API Документация

Базовый URL - http://localhost:8000/api



Эндпоинты 
(
Метод	URL	Описание	Статус
GET	/quests/	Список квестов с пагинацией	200
POST	/quests/	Создать квест	201
GET	/quests/{id}/	Получить квест	200
PUT	/quests/{id}/	Полное обновление	200
PATCH	/quests/{id}/	Частичное обновление	200
DELETE	/quests/{id}/	Мягкое удаление	204
POST	/quests/{id}/activate/	Активировать квест	200
POST	/quests/{id}/complete/	Завершить квест	200
POST	/quests/{id}/restore/	Восстановить удалённый	200
GET	/quests/statistics/	Статистика по квестам	200
)

Параметры пагинации

(
GET /api/quests/?page=1&limit=10&ordering=-created_at&search=dragon&status=active
Параметр	Тип	По умолчанию	Описание
page	int	1	Номер страницы (≥ 1)
limit	int	10	Записей на странице (1-100)
ordering	string	-created_at	Сортировка
search	string	—	Поиск по названию
status	string	—	Фильтр по статусу
)

Доступные значения ordering:
(
created_at, -created_at
title, -title
difficulty, -difficulty
reward_gold, -reward_gold
Доступные значения status:

draft, active, completed, failed
)
8. Миграции выполняются автоматически при запуске контейнера