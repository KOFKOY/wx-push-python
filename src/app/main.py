from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from src.app.db import db
from src.app.schemas import PushRequest, PushResponse
from src.app.wechat import wechat_client
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接数据库
    logger.info("Connecting to database...")
    await db.connect()
    yield
    # 关闭时断开连接
    logger.info("Disconnecting from database...")
    await db.disconnect()

app = FastAPI(title="WeChat Push Service", lifespan=lifespan)

# 要忽略日志的路径
IGNORE_PATHS = {"/api/heartbeat", "/api/sysinfo"}
access_logger = logging.getLogger(__name__)
class FilterAccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)

        path = request.url.path
        if path not in IGNORE_PATHS:
            process_time = (time.time() - start_time) * 1000
            client_host = request.client.host
            client_port = request.client.port
            method = request.method
            status_code = response.status_code

            access_logger.info(
                '%s:%s - "%s %s HTTP/1.1" %d %.2fms',
                client_host,
                client_port,
                method,
                path,
                status_code,
                process_time,
            )

        return response

# 注意：要在其他中间件之前添加
app.add_middleware(FilterAccessLogMiddleware)


@app.post("/push", response_model=PushResponse)
async def push_message(request: PushRequest):
    logger.info(f"Received push request: {request.title}")
    result = await wechat_client.send_message(request)
    if result["code"] != 0:
        # 即使发送失败，也可以返回 500
        # raise HTTPException(status_code=500, detail=result["message"])
        return {"code": 0, "message": result["message"]}
    return result

@app.post("/api/heartbeat")
async def heartbeat():
    return {"status": "fuck"}

@app.post("/api/sysinfo")
async def sysinfo():
    return {"status": "fuck"}



from src.app.db import db
@app.get("/add_proxy")
async def add_proxy(proxy: str):
    proxy_info = proxy.split("\n")
    proxy_list = []
    for proxy in proxy_info:
        proxy = proxy.strip()
        if len(proxy) == 0:
            continue
        proxy_info = proxy.split(":")
        port = 443
        protocol = "socks5"
        user = None
        password = None
        if len(proxy_info) == 1:
            ip = proxy_info[0]
        elif len(proxy_info) == 2:
            ip = proxy_info[0]
            port = int(proxy_info[1])
        elif len(proxy_info) == 3:
            user = proxy_info[0]
            password = proxy_info[1].split("@")[0]
            ip = proxy_info[1].split("@")[1]
            port = int(proxy_info[2])
        proxy_list.append((ip, port, protocol, user, password))
    await db.execute_many('INSERT INTO proxies (ip, port, protocol, "user", "pw") VALUES ($1, $2, $3, $4, $5)', proxy_list)
    return {"status": "ok"}