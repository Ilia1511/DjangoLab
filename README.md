# Quest Aggregator API

REST API на Django REST Framework для лабораторных работ: JWT в cookies, OAuth через Yandex, CRUD по `items/quests`, Redis-кеш, MongoDB, MinIO и RabbitMQ-события.

## Запуск

```bash
docker compose up --build
```

После запуска:

- Swagger UI: `http://localhost:8000/api/docs/`
- MongoDB: `localhost:27017`
- Redis: `localhost:6379`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- RabbitMQ Management UI: `http://localhost:15672`

## .env.example

Пример файла окружения: [.env.example](C:/Users/ximik/Desktop/DjangoLab/WebApp/.env.example)

```env
DB_USER=student
DB_PASSWORD=student_secure_password
DB_NAME=wp_labs
MONGO_URI=mongodb://student:student_secure_password@mongo:27017/wp_labs?authSource=admin

SECRET_KEY=change-me-in-production
JWT_SECRET_KEY=change-me-in-production
DEBUG=True
NODE_ENV=development
SWAGGER_ENABLED=true

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password_change_in_prod
CACHE_TTL_DEFAULT=300

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=minio_secure_password_change_in_prod
MINIO_BUCKET=wp-labs-files
MINIO_USE_SSL=false
MAX_FILE_SIZE=10485760

RABBITMQ_USER=student
RABBITMQ_PASS=student_secure_rabbit_pass_change_in_prod
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_EXCHANGE=app.events
RABBITMQ_DLX=app.dlx
QUEUE_USER_REGISTERED=wp.auth.user.registered

SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=your_email@yandex.ru
SMTP_PASS=your_app_password
SMTP_FROM=your_email@yandex.ru
SMTP_SECURE=true
```

## Инфраструктура

- `mongo` - основная база данных, защищена логином и паролем.
- `redis` - кеш списков, профилей, метаданных файлов и JTI access-токенов.
- `minio` - S3-compatible объектное хранилище для загруженных файлов.
- `rabbitmq` - брокер сообщений для событий приложения и фоновой отправки email.
- `web` - Django/DRF API.
- `nginx` - reverse proxy.

MongoDB хранит данные в коллекциях:

- `users`
- `tokens`
- `quests`
- `files`

Проверка документов через CLI:

```bash
docker compose exec mongo mongosh -u student -p student_secure_password --authenticationDatabase admin wp_labs
db.users.find()
db.quests.find()
db.tokens.find()
db.files.find()
```

## API

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/whoami/`
- `POST /api/auth/logout/`
- `POST /api/auth/logout-all/`
- `POST /api/auth/change-password/`
- `GET /api/profile/`
- `POST /api/profile/`
- `POST /api/files/`
- `GET /api/files/{fileId}/`
- `DELETE /api/files/{fileId}/`
- `GET /api/items/`
- `POST /api/items/`
- `GET /api/items/{id}/`
- `PUT /api/items/{id}/`
- `PATCH /api/items/{id}/`
- `DELETE /api/items/{id}/`
- `POST /api/items/{id}/activate/`
- `POST /api/items/{id}/complete/`
- `POST /api/items/{id}/restore/`

Маршруты `/api/quests/...` сохранены как совместимые алиасы.

## MongoDB Models

Квест хранится как документ:

```json
{
  "_id": "ObjectId",
  "title": "Dragon quest",
  "description": "Quest description",
  "status": "draft",
  "difficulty": "hard",
  "reward_gold": 2500,
  "reward_experience": 900,
  "owner": {
    "id": "user ObjectId",
    "username": "ivan_petrov"
  },
  "createdAt": "date-time",
  "updatedAt": "date-time",
  "deletedAt": null
}
```

Файл хранится в MongoDB только как метаданные:

```json
{
  "_id": "uuid",
  "userId": "mongo-user-id",
  "originalName": "avatar.png",
  "objectKey": "users/{userId}/{fileId}/avatar.png",
  "size": 12345,
  "mimetype": "image/png",
  "bucket": "wp-labs-files",
  "isUsed": true,
  "createdAt": "date-time",
  "updatedAt": "date-time",
  "deletedAt": null
}
```

Сами файлы не сохраняются в MongoDB или файловой системе приложения. Они лежат в MinIO, а `objectKey` и `bucket` используются только внутри сервиса и не отдаются в публичных Swagger-ответах.

## Redis

Ключи кеша:

- `wp:items:user:{userId}:list:*`
- `wp:items:user:{userId}:item:{itemId}`
- `wp:users:profile:{userId}`
- `wp:files:{fileId}:meta`
- `wp:auth:user:{userId}:access:{jti}`

Проверка Redis:

```bash
docker compose exec redis redis-cli --pass redis_secure_password_change_in_prod
KEYS 'wp:*'
GET wp:files:<fileId>:meta
TTL wp:files:<fileId>:meta
```

## MinIO

Откройте консоль `http://localhost:9001` и войдите с:

- login: `MINIO_ACCESS_KEY`
- password: `MINIO_SECRET_KEY`

Бакет `MINIO_BUCKET` создается приложением автоматически при первой загрузке файла. Разрешены аватары с MIME-типами `image/png`, `image/jpeg`, `image/jpg`, максимальный размер задается через `MAX_FILE_SIZE`.

## RabbitMQ

При успешной регистрации `POST /api/auth/register/` приложение публикует событие:

```json
{
  "eventId": "uuid",
  "eventType": "user.registered",
  "timestamp": "date-time",
  "payload": {
    "userId": "mongo-user-id",
    "email": "user@example.com",
    "username": "ivan_petrov",
    "displayName": "Ivan"
  },
  "metadata": {
    "attempt": 0,
    "source": "django-api"
  }
}
```

RabbitMQ topology:

- exchange: `app.events`, direct, durable
- routing key: `user.registered`
- queue: `wp.auth.user.registered`, durable
- DLX: `app.dlx`
- DLQ: `wp.auth.user.registered.dlq`

Consumer запускается фоновым потоком вместе с `runserver`. Он отправляет приветственное письмо через SMTP, подтверждает сообщение только после успешной отправки и хранит обработанные `eventId` в Redis на 24 часа:

```bash
docker compose logs -f web
docker compose exec redis redis-cli --pass redis_secure_password_change_in_prod KEYS 'wp:events:processed:*'
```

RabbitMQ Management UI доступен на `http://localhost:15672`.

Логин:

```text
student
```

Пароль:

```text
student_secure_rabbit_pass_change_in_prod
```

Для проверки очередей откройте вкладку `Queues and Streams` и проверьте:

- `wp.auth.user.registered`
- `wp.auth.user.registered.dlq`

Если SMTP-настройки неверные, consumer выполнит повторные попытки. После 3 неудач сообщение попадет в DLQ.

## Health Checks и Kubernetes

Health-эндпоинты:

- `GET /health` - общий статус приложения.
- `GET /health/live` - liveness probe, минимальная проверка живости Django-процесса.
- `GET /health/ready` - readiness probe, проверяет доступность MongoDB, Redis, RabbitMQ и MinIO.

`/health/ready` возвращает `200` только если все зависимости доступны. Если хотя бы одна зависимость недоступна, endpoint возвращает `503`.

Сборка Docker-образа:

```bash
docker build -t wp-labs/api:1.0.0 .
```

Применение Kubernetes-манифестов:

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/02-mongodb/ \
             -f k8s/03-redis/ \
             -f k8s/04-minio/ \
             -f k8s/05-rabbitmq/ \
             -f k8s/06-api/
```

Проверка ресурсов:

```bash
kubectl get all -n wp-labs
```

Проброс API:

```bash
kubectl port-forward svc/api 4200:4200 -n wp-labs
```

Проверка health endpoints:

```bash
curl http://localhost:4200/health
curl http://localhost:4200/health/live
curl http://localhost:4200/health/ready
```

Масштабирование API:

```bash
kubectl scale deployment/api --replicas=4 -n wp-labs
```

При регистрации пользователя используется Redis distributed lock:

```text
lock:user:create:{email}
```

Это защищает критическую секцию создания пользователя от одновременной обработки одинаковой регистрации на разных pod-ах.

Логи подов:

```bash
kubectl get pods -n wp-labs
kubectl logs -f <pod-name> -n wp-labs
```

## PostgreSQL vs MongoDB

PostgreSQL хорошо подходит для строгих схем, транзакций и сложных связей через JOIN. MongoDB удобнее, когда данные естественно читаются документами: например, квест вместе с короткими данными владельца. В этой версии приложение хранит квесты, пользователей, токены и метаданные файлов как документы, а валидация схемы выполняется на уровне DRF-сериализаторов и сервисов.
