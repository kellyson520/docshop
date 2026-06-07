from typing import Any, Optional


def success_response(data: Any = None, message: str = "success") -> dict:
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


def error_response(code: int, message: str) -> dict:
    return {
        "code": code,
        "message": message,
        "data": None,
    }
