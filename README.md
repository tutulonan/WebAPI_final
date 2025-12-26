# RSS Monitor - Асинхронный Backend на FastAPI

*Асинхронный backend на FastAPI: REST + WebSocket + фоновая задача + NATS*

Проект демонстрирует современную event-driven архитектуру backend-сервиса для мониторинга RSS-лент:
- **REST API** для управления RSS-постами
- **WebSocket** для реального времени
- **Фоновая задача** парсинга RSS (Habr.com)
- **NATS** для асинхронной коммуникации
- **Асинхронная работа** с БД (SQLite/SQLAlchemy)

## Запуск

### 1. Клонирование и настройка
```bash
# Клонируйте репозиторий
git clone https://github.com/tutulonan/WebAPI_final.git
cd WebAPI_final

# Установите зависимости
pip install -r requirements.txt
```

### 2. Запуск NATS сервера
```bash
docker run -p 4222:4222 nats
```

### 3. Запуск приложения
```bash
python run.py
```

### 4. Доступ к сервисам
После запуска сервис будет доступен по следующим адресам:
- **API:** http://localhost:8000
- **Документация (Swagger):** http://localhost:8000/docs
- **WebSocket** ws://localhost:8000/ws/posts


## Основные возможности

### REST API (Posts)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/posts/` | Получить список постов |
| `GET` | `/posts/{id}` | Получить пост по ID |
| `POST` | `/posts/` | Создать новый пост |
| `PATCH` | `/posts/{id}` | Обновить пост |
| `DELETE` | `/posts/{id}` | Удалить пост |
| `POST` | `/posts/run` | Принудительно запустить парсинг RSS |

### WebSocket
- **Endpoint**: `/ws/posts?client_id=ваш_id`
- **Поддерживаемые события**:
  - `ping` → `pong` (проверка соединения)
  - `get_info` → информация о подключениях
- **Автоматические уведомления**:
  - `new_post` - при добавлении новых постов из RSS
  - `post_updated` - при обновлении поста
  - `post_deleted` - при удалении поста
  - `external_post` - при получении постов через NATS
  - `manual_post_created` - при ручном создании поста

### Фоновая задача
- Автоматически парсит RSS Habr.com каждые 5 минут (настраивается)
- Сохраняет новые посты в базу данных
- Отправляет уведомления через WebSocket и NATS

### NATS Integration
- Публикация событий в канал `rss.updates`
- Подписка на внешние события
- Асинхронная обработка сообщений

## Тестирование

### Тестирование WebSocket
1. Откройте файл `test_websocket.html` в браузере
2. Нажмите "Connect"
3. Используйте "Send Ping" для проверки соединения
4. Выполните POST запрос на `/posts/run` для получения реальных событий
