from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import asyncio
import logging
from app.logging_config import setup_colored_logging
import json
from datetime import datetime

from app.utils.json_helpers import safe_json_dumps
from app.db.session import init_db
from app.nats.client import init_nats, close_nats
from app.ws.manager import manager
from app.api.posts import router as posts_router
from app.services.rss import background_rss_worker

setup_colored_logging()
logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт
    await init_db()
    await init_nats()

    bg_task = asyncio.create_task(background_rss_worker())
    logger.info("Приложение запущено")

    yield

    # Остановка
    global background_task_running
    background_task_running = False
    bg_task.cancel()
    try:
        await bg_task
    except asyncio.CancelledError:
        pass

    await close_nats()
    logger.info("Приложение остановлено")


app = FastAPI(
    lifespan=lifespan,
    title="RSS Monitor",
    version="1.0"
)

app.include_router(posts_router)


@app.websocket("/ws/posts")
async def websocket_endpoint(websocket: WebSocket):
    # Принимаем client_id из query параметров
    client_id = websocket.query_params.get("client_id")

    await manager.connect(websocket, client_id)

    try:
        while True:
            # Принимаем сообщения от клиента
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                event = message.get("event", "unknown")

                # Логируем входящие сообщения
                client_info = manager.connection_info.get(websocket, {})
                client_id = client_info.get("id", "unknown")

                logger.info(f" ← {client_id}: {event}")
                logger.debug(f"Сообщение: {data[:100]}...")

                # Обработка специфичных команд от клиента
                if event == "ping":
                    # Используем safe_json_dumps для ответа
                    response = safe_json_dumps({
                        "event": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                    await websocket.send_text(response)

                elif event == "get_info":
                    connections_info = await manager.get_connections_info()
                    response = safe_json_dumps({
                        "event": "connections_info",
                        "data": connections_info,
                        "timestamp": datetime.now().isoformat()
                    })
                    await websocket.send_text(response)

            except json.JSONDecodeError:
                logger.warning(f"Некорректный JSON от клиента: {data}")

    except WebSocketDisconnect:
        logger.info("WebSocket отключен (нормально)")
    except Exception as e:
        logger.error(f"Ошибка WebSocket: {e}")
    finally:
        manager.disconnect(websocket)


# Новый endpoint для получения информации о подключениях
@app.get("/ws/connections")
async def get_ws_connections():
    """Получить информацию о всех активных WebSocket подключениях"""
    connections_info = await manager.get_connections_info()
    return {
        "total_connections": len(connections_info),
        "connections": connections_info
    }