import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any
import logging

logger = logging.getLogger(__name__)


def json_serializer(obj: Any) -> Any:
    """Кастомный сериализатор для JSON"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, 'dict'):
        return obj.dict()
    elif hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        logger.warning(f"Type {type(obj)} not JSON serializable, converting to string")
        return str(obj)


def safe_json_dumps(data: dict, **kwargs) -> str:
    """Безопасная сериализация в JSON"""
    return json.dumps(data, default=json_serializer, ensure_ascii=False, **kwargs)