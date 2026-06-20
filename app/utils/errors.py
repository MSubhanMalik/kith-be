import json
import os

from fastapi import HTTPException


_errors = {}
_errors_path = os.path.join(os.path.dirname(__file__), "errors.json")

with open(_errors_path, "r") as f:
    _errors = json.load(f)


class AppError(HTTPException):
    def __init__(self, code: str, detail: str = None):
        error = _errors.get(code, _errors["INTERNAL_SERVER_ERROR"])
        super().__init__(
            status_code=error["status"],
            detail=detail or error["message"],
        )
        self.error_code = code


def get_error(code: str, detail: str = None) -> AppError:
    return AppError(code, detail)
