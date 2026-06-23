from fastapi import FastAPI
import requests
from app.schemas import PushRequest, PushResponse
from app.wechat import wechat_client
import logging
from app.logging_utils import LoggingContextRoute

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


app = FastAPI(title="WeChat Push Service")
app.router.route_class = LoggingContextRoute


@app.post("/push", response_model=PushResponse)
async def push_message(request: PushRequest):
    logger.info(f"Received push request: {request.title}")
    result = await wechat_client.send_message(request)
    return result

@app.get("/webhook")
async def webhook(msg: str,response_model=PushResponse):
    logger.info(f"Received webhook message: {msg}")
    requests.post("https://open.feishu.cn/open-apis/bot/v2/hook/7c15f506-c4e6-44cf-899e-8e89eabbb177", json={"msg_type": "text", "content": {"text": msg}})
    return PushResponse.success()