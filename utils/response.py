from flask import jsonify
from typing import Any, Optional


class ApiResponse:
    """统一 API 响应格式"""

    @staticmethod
    def success(data: Any = None, message: str = "success") -> tuple:
        """成功响应"""
        return jsonify({
            "code": 200,
            "message": message,
            "data": data
        }), 200

    @staticmethod
    def error(message: str, code: int = 400, data: Any = None) -> tuple:
        """错误响应"""
        return jsonify({
            "code": code,
            "message": message,
            "data": data
        }), code