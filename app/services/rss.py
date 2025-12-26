import feedparser
import asyncio
from typing import List, Optional
from sqlalchemy import text
from app.schemas.post import RSSPostCreate
from app.config import settings
from app.models.post import RSSPost
from sqlalchemy.ext.asyncio import AsyncSession
from app.nats.client import publish_post_event
from app.ws.manager import manager
import logging
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn")
background_task_running = True


async def fetch_rss_feed() -> Optional[List[RSSPostCreate]]:
    """Асинхронно получает и парсит RSS-ленту"""
    try:
        def _parse_feed(url):
            return feedparser.parse(url)

        feed = await asyncio.to_thread(_parse_feed, settings.RSS_URL)

        if feed.bozo:
            raise Exception(f"Ошибка парсинга RSS: {feed.bozo_exception}")

        posts = []
        for entry in feed.entries[:10]:
            category = None
            if hasattr(entry, "tags") and entry.tags:
                category = entry.tags[0]["term"] if entry.tags else None

            post = RSSPostCreate(
                title=entry.title,
                link=entry.link,
                summary=entry.get("summary", "")[:1000],
                published=getattr(entry, "published", None),
                author=getattr(entry, "author", "unknown"),
                category=category,
                source="habr"
            )
            posts.append(post)

        return posts

    except Exception as e:
        logger.error(f"Ошибка получения RSS: {e}")
        return None


async def save_posts_to_db(posts: List[RSSPostCreate], db: AsyncSession) -> int:
    """Сохраняет новые посты (избегая дубликатов по `link`)"""
    added = 0
    for post_data in posts:
        result = await db.execute(
            text("SELECT 1 FROM rss_posts WHERE link = :link"),
            {"link": post_data.link}
        )
        if result.fetchone():
            continue

        db_post = RSSPost(**post_data.model_dump())
        db.add(db_post)
        await db.flush()
        await db.refresh(db_post)

        added += 1

        await publish_post_event(
            post_id=db_post.id,
            title=db_post.title,
            link=db_post.link,
            source=db_post.source
        )

        await manager.broadcast({
            "event": "new_post",
            "payload": {
                "id": db_post.id,
                "title": db_post.title,
                "link": db_post.link,
                "source": db_post.source,
                "category": db_post.category
            }
        })

    await db.commit()
    return added


async def background_rss_worker():
    """Фоновая задача: раз в N секунд парсит RSS и сохраняет новые посты"""
    logger.info(f"Фоновая задача запущена (интервал: {settings.BACKGROUND_TASK_INTERVAL} сек)")

    while background_task_running:
        try:
            posts = await fetch_rss_feed()
            if posts:
                async with AsyncSessionLocal() as db:
                    added = await save_posts_to_db(posts, db)
                    if added:
                        logger.info(f"Добавлено {added} новых постов")
            else:
                logger.warning("RSS-лента пуста или ошибка")

        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче: {e}")

        await asyncio.sleep(settings.BACKGROUND_TASK_INTERVAL)