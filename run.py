import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Слушаем все интерфейсы
        port=8000,
        reload=True,
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )