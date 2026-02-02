from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from src.app.db import db
from src.app.schemas import PushRequest, PushResponse
from src.app.wechat import wechat_client
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
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

@app.post("/push", response_model=PushResponse)
async def push_message(request: PushRequest):
    logger.info(f"Received push request: {request.title}")
    result = await wechat_client.send_message(request)
    if result["code"] != 0:
        # 即使发送失败，也可以返回 500
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.get("/health")
async def health_check():
    return {"status": "ok"}



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