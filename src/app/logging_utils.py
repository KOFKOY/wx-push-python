from fastapi import Request, Response
from fastapi.routing import APIRoute
from typing import Callable
import time
import logging

logger = logging.getLogger(__name__)

# 要忽略日志的路径
IGNORE_PATHS = {"/api/heartbeat", "/api/sysinfo", "/health"}

class LoggingContextRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            if request.url.path in IGNORE_PATHS:
                return await original_route_handler(request)

            start_time = time.time()

            # 读取请求体
            request_body = ""
            try:
                body_bytes = await request.body()
                if body_bytes:
                    request_body = body_bytes.decode("utf-8")
                    # 简单压缩一下日志，去除换行
                    request_body = request_body.replace('\n', '').replace('\r', '')
            except Exception:
                request_body = "<read failed>"

            response: Response = await original_route_handler(request)

            process_time = (time.time() - start_time) * 1000

            # 读取响应体
            response_body = ""
            if hasattr(response, "body"):
                 try:
                    response_body = response.body.decode("utf-8")
                 except:
                    response_body = "<decode failed>"

            logger.info(
                f"Path: {request.url.path} | "
                f"Time: {process_time:.2f}ms | "
                f"Request: {request_body} | "
                f"Response: {response_body}"
            )

            return response

        return custom_route_handler
