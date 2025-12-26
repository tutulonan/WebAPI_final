import logging
from nats.aio.client import Client as NATS
from app.config import settings
from app.ws.manager import manager
from app.schemas.post import RSSUpdateEvent

logger = logging.getLogger("uvicorn")
nc: NATS = None


async def init_nats():
    global nc
    try:
        nc = NATS()
        await nc.connect(settings.NATS_URL)
        logger.info("NATS подключен")
    except Exception as e:
        logger.error(f"Ошибка подключения к NATS: {e}")
        raise

    # Подписка на события (внешние посты)
    async def message_handler(msg):
        try:
            data = msg.data.decode()
            event = RSSUpdateEvent.model_validate_json(data)
            logger.info(f"NATS received: [{event.source}] {event.title}")

            # Отправляем в WebSocket
            await manager.broadcast({
                "event": "external_post",
                "payload": event.model_dump(),
                "timestamp": event.model_dump().get("timestamp", None)
            })
        except Exception as e:
            logger.error(f"NATS handler error: {e}")

    await nc.subscribe(settings.NATS_SUBJECT, cb=message_handler)
    logger.info(f"Подписка NATS на канал: {settings.NATS_SUBJECT}")


async def publish_post_event(post_id: int, title: str, link: str, source: str = "habr"):
    if not nc or not nc.is_connected:
        return
    event = RSSUpdateEvent(
        post_id=post_id,
        title=title,
        link=link,
        source=source
    )
    try:
        await nc.publish(settings.NATS_SUBJECT, event.model_dump_json().encode())
        # Безопасное логирование заголовка
        safe_title = event.title[:30].strip()
        logger.info(f"NATS published: {safe_title}...")
    except Exception as e:
        logger.error(f"NATS publish error: {e}")


async def close_nats():
    global nc
    if nc:
        await nc.close()
        logger.info("NATS отключен")