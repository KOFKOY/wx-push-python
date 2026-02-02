import logging
import time
import requests
import asyncio
import threading
from src.app.config import get_settings
from src.app.schemas import PushRequest, MessageType
from src.app.proxy import get_valid_proxies_list

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
                resp = requests.get(url, params=params)
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

    def _send_msg_sync(self, proxy: str | None,token: str, message_body: dict) -> dict | None:
        """
        同步发送消息
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        # 使用 Session 复用链接
        with requests.Session() as session:
            if proxies:
                logger.info(f"使用代理: {proxy}")
                session.proxies.update(proxies)

            try:
                send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
                resp = session.post(send_url, json=message_body, timeout=10.0)
                data = resp.json()

                if data.get("errcode") == 0:
                    logger.info("消息发送成功")
                    return {"code": 0, "message": "success", "data": data}
                else:
                    logger.warning(f"微信API错误: {data}")
                    # 返回 None 表示失败，继续重试
                    return {"code": 500,  "data": data}

            except Exception as e:
                logger.error(f"网络错误发送消息: {e}")
                return {"code": 500, "data": str(e)}

    async def send_message(self, request: PushRequest):
        """
        发送消息，包含重试逻辑
        """
        # 1. 获取可用代理列表
        proxies_list = await get_valid_proxies_list(limit=3)
        # 代理重试队列：可用代理 -> None (本地IP)
        retry_proxies = proxies_list + [None]

        # 转换消息体
        message_body = self._build_message_body(request)

        loop = asyncio.get_running_loop()

        # 获取 Token (复用 proxy session) 不需要使用代理
        token = self._get_access_token_sync()
        if not token:
            return {"code": 500, "message": "获取token失败"}

        error_msg = []

        for i, proxy in enumerate(retry_proxies):
            is_last_attempt = (i == len(retry_proxies) - 1)
            logger.info(f"Attempt {i+1}/{len(retry_proxies)} sending message using {'Local IP' if proxy is None else proxy}")

            # 在线程池中执行同步请求
            result = await loop.run_in_executor(None, self._send_msg_sync, proxy,token, message_body)

            if result["code"] == 0:
                return result
            else:
                error_msg.append(result["data"])

            if is_last_attempt:
                logger.error("All attempts failed")
                return {"code": 500, "message": f"本地IP及代理均失效, 请检查可信IP和代理, {error_msg}"}

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
