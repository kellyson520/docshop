from typing import Any, Optional

_TOP_LEVEL_KEYS = frozenset({"code", "message", "data"})


def success_response(data: Any = None, message: str = "success") -> dict:
    response = {
        "code": 0,
        "message": message,
        "data": data,
    }
    if isinstance(data, dict):
        for key, value in data.items():
            if key in _TOP_LEVEL_KEYS:
                continue
            response[key] = value
    return response


def error_response(code: int, message: str) -> dict:
    return {
        "code": code,
        "message": message,
        "data": None,
    }
