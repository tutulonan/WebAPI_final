from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.post import RSSPostCreate, RSSPostUpdate, RSSPostResponse
from app.services.rss import fetch_rss_feed, save_posts_to_db
from app.nats.client import publish_post_event
from app.ws.manager import manager
from app.models.post import RSSPost

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/", response_model=list[RSSPostResponse])
async def get_posts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM rss_posts ORDER BY created_at DESC LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip}
    )
    rows = result.fetchall()
    return [RSSPostResponse.model_validate(dict(r._mapping)) for r in rows]


@router.get("/{post_id}", response_model=RSSPostResponse)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM rss_posts WHERE id = :id"),
        {"id": post_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Post not found")
    return RSSPostResponse.model_validate(dict(row._mapping))


@router.post("/", response_model=RSSPostResponse)
async def create_post(post: RSSPostCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем дубликат по link
    existing = await db.execute(
        text("SELECT 1 FROM rss_posts WHERE link = :link"),
        {"link": post.link}
    )
    if existing.fetchone():
        raise HTTPException(400, "Post with this link already exists")

    db_post = RSSPost(**post.model_dump())
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)

    await publish_post_event(db_post.id, db_post.title, db_post.link, db_post.source)
    await manager.broadcast({
        "event": "manual_post_created",
        "payload": RSSPostResponse.model_validate(db_post).model_dump()
    })

    return RSSPostResponse.model_validate(db_post)


@router.patch("/{post_id}", response_model=RSSPostResponse)
async def update_post(post_id: int, update_data: RSSPostUpdate, db: AsyncSession = Depends(get_db)):
    # Получаем текущую запись
    result = await db.execute(
        text("SELECT * FROM rss_posts WHERE id = :id"),
        {"id": post_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Post not found")

    # Подготавливаем обновление
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return RSSPostResponse.model_validate(dict(row._mapping))

    set_clause = ", ".join([f"{k} = :{k}" for k in update_dict])
    update_dict["id"] = post_id

    await db.execute(
        text(f"UPDATE rss_posts SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
        update_dict
    )
    await db.commit()

    # Возвращаем обновлённую запись
    result = await db.execute(
        text("SELECT * FROM rss_posts WHERE id = :id"),
        {"id": post_id}
    )
    updated_row = result.fetchone()
    resp = RSSPostResponse.model_validate(dict(updated_row._mapping))

    await manager.broadcast({"event": "post_updated", "payload": resp.model_dump()})
    return resp


@router.delete("/{post_id}")
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("DELETE FROM rss_posts WHERE id = :id"),
        {"id": post_id}
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Post not found")
    await db.commit()

    await manager.broadcast({"event": "post_deleted", "post_id": post_id})
    return {"ok": True}


@router.post("/run")
async def run_rss_fetch(db: AsyncSession = Depends(get_db)):
    posts = await fetch_rss_feed()
    if not posts:
        return {"status": "error", "message": "Не удалось получить RSS"}

    added = await save_posts_to_db(posts, db)
    return {"status": "ok", "added": added}