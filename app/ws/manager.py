from fastapi import WebSocket
from typing import List
import logging
import json
from datetime import datetime
from app.utils.json_helpers import safe_json_dumps

logger = logging.getLogger("websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()

        if not client_id:
            client_id = f"client_{len(self.active_connections) + 1}_{datetime.now().strftime('%H%M%S')}"

        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "id": client_id,
            "connected_at": datetime.now().isoformat(),
            "ip": websocket.client.host if websocket.client else "unknown"
        }

        logger.info(f"WebSocket подключен: {client_id} "
                    f"(IP: {self.connection_info[websocket]['ip']})")
        logger.info(f"Активных подключений: {len(self.active_connections)}")

        # Отправляем приветственное сообщение
        await self.send_personal_message({
            "event": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "message": "WebSocket подключен успешно"
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            client_info = self.connection_info.get(websocket, {})
            client_id = client_info.get("id", "unknown")

            self.active_connections.remove(websocket)

            if websocket in self.connection_info:
                del self.connection_info[websocket]

            logger.info(f"WebSocket отключен: {client_id}")
            logger.info(f"Активных подключений: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            serialized_message = safe_json_dumps(message)
            await websocket.send_text(serialized_message)

            client_id = self.connection_info.get(websocket, {}).get("id", "unknown")
            event_type = message.get("event", "unknown")

            logger.debug(f"→ {client_id}: {event_type}")

        except Exception as e:
            logger.error(f"Ошибка отправки сообщения {client_id}: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict, exclude: List[WebSocket] = None):
        if exclude is None:
            exclude = []

        event_type = message.get("event", "unknown")

        # Сначала сериализуем сообщение для логирования
        try:
            # Функция для преобразования datetime в строку
            def serialize_datetime(obj):
                import json
                from datetime import datetime, date

                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif hasattr(obj, 'dict'):
                    return obj.dict()
                elif hasattr(obj, 'model_dump'):
                    return obj.model_dump()
                raise TypeError(f"Type {type(obj)} not serializable")

            # Сериализуем для логирования
            message_for_log = json.dumps(message, default=serialize_datetime, ensure_ascii=False)
            message_str = message_for_log[:100] + "..." if len(message_for_log) > 100 else message_for_log

            logger.info(f"Broadcasting: {event_type}")
            logger.debug(f"Сообщение: {message_str}")

        except Exception as e:
            logger.error(f"Ошибка сериализации для лога: {e}")
            message_str = str(message)[:100]

        logger.info(f"Получателей: {len(self.active_connections) - len(exclude)}")

        disconnected = []
        for connection in self.active_connections[:]:
            if connection in exclude:
                continue

            try:
                # Сериализуем сообщение перед отправкой
                serialized_message = json.dumps(message, default=serialize_datetime, ensure_ascii=False)
                await connection.send_text(serialized_message)

                client_id = self.connection_info.get(connection, {}).get("id", "unknown")
                logger.debug(f"   → отправлено {client_id}")

            except Exception as e:
                client_id = self.connection_info.get(connection, {}).get("id", "unknown")
                logger.error(f"Ошибка отправки {client_id}: {e}")
                disconnected.append(connection)

        # Удаляем отключенные соединения
        for connection in disconnected:
            self.disconnect(connection)

    async def get_connections_info(self):
        """Получить информацию о всех активных подключениях"""
        info = []
        for websocket in self.active_connections:
            if websocket in self.connection_info:
                info.append(self.connection_info[websocket])
        return info

    async def send_to_client(self, client_id: str, message: dict):
        """Отправить сообщение конкретному клиенту"""
        for websocket, info in self.connection_info.items():
            if info.get("id") == client_id:
                await self.send_personal_message(message, websocket)
                return True
        logger.warning(f"Клиент {client_id} не найден")
        return False


manager = ConnectionManager()