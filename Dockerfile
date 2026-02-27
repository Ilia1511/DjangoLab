# Используем официальный образ Python
FROM python:3.13

# Устанавливаем переменные окружения, чтобы Python не создавал .pyc и выводил логи сразу
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости системы (нужны для сборки некоторых библиотек Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Команда для запуска (для разработки)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]