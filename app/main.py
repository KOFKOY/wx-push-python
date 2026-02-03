from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.db import db
from app.schemas import PushRequest, PushResponse
from app.wechat import wechat_client
import logging


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

from app.logging_utils import LoggingContextRoute

app = FastAPI(title="WeChat Push Service", lifespan=lifespan)
app.router.route_class = LoggingContextRoute


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


from app.proxy import check_and_update_all_proxies
@app.get("/check_proxy")
async def check_proxy():
    result = await check_and_update_all_proxies()
    return {"status": "ok", "data": result}


from app.proxy import check_add_proxy as service_check_add_proxy
from fastapi import Body

@app.post("/add_proxy")
async def add_proxy(content: str = Body(..., media_type="text/plain")):
    """
    接收纯文本代理信息，一行一个，格式: protocol://ip:port ...
    解析并检测可用性，入库
    """
    try:
        count = await service_check_add_proxy(content)
        return {"status": "ok", "data": f'成功入库代理数量: {count}'}
    except Exception as e:
        logger.error(f"处理代理添加请求失败: {e}")
        return {"status": "error", "message": str(e)}