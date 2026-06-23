import logging
import time
import requests
import asyncio
import threading
from app.config import get_settings
from app.schemas import PushRequest, MessageType

settings = get_settings()
logger = logging.getLogger(__name__)

class WeChatClient:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = 0
        self._lock = threading.Lock()

    def _get_access_token_sync(self) -> str | None:
        """
        获取 Access Token，带缓存 (同步方法)
        """
        with self._lock:
            if self.access_token and time.time() < self.token_expires_at:
                return self.access_token

            # 需要刷新 Token
            url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            params = {
                "corpid": settings.CORP_ID,
                "corpsecret": settings.CORP_SECRET
            }

            try:
                resp = requests.get(url, params=params, timeout=10.0)
                data = resp.json()
                if data.get("errcode") == 0:
                    self.access_token = data.get("access_token")
                    # 提前 200 秒过期
                    self.token_expires_at = time.time() + data.get("expires_in", 7200) - 200
                    return self.access_token
                else:
                    logger.error(f"Get access token failed: {data}")
            except Exception as e:
                logger.error(f"Get access token error: {e}")
            return None

    def _send_msg_sync(self, token: str, message_body: dict) -> dict:
        """
        同步发送消息
        """
        with requests.Session() as session:
            try:
                send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
                resp = session.post(send_url, json=message_body, timeout=10.0)
                data = resp.json()

                if data.get("errcode") == 0:
                    logger.info("消息发送成功")
                    return {"code": 0, "message": "success", "data": data}
                else:
                    logger.warning(f"微信API错误: {data}")
                    return {"code": 500, "message": "微信接口返回失败", "data": data}

            except Exception as e:
                logger.error(f"网络错误发送消息: {e}")
                return {"code": 500, "message": "网络请求失败", "data": str(e)}

    async def send_message(self, request: PushRequest):
        """
        发送消息（直连企业微信，不使用代理）
        """
        loop = asyncio.get_running_loop()

        token = self._get_access_token_sync()
        if not token:
            return {"code": 500, "message": "获取token失败"}

        message_body = self._build_message_body(request)
        return await loop.run_in_executor(None, self._send_msg_sync, token, message_body)

    def _build_message_body(self, request: PushRequest) -> dict:
        base = {
            "touser": request.target,
            "agentid": settings.AGENT_ID,
            "enable_duplicate_check": 0,
        }

        if request.type == MessageType.TEXT_CARD:
            base["msgtype"] = "textcard"
            base["textcard"] = {
                "title": request.title,
                "description": request.content,
                "url": request.url,
                "btntxt": "详情"
            }
        elif request.type == MessageType.TEXT:
            base["msgtype"] = "text"
            base["text"] = {
                "content": f"{request.title}\n{request.content}\n{request.url}"
            }

        return base

wechat_client = WeChatClient()
