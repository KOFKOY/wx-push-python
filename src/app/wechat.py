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
        self.cached_proxy = None # 缓存成功的代理

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
                # 获取token时不一定非要用代理，或者可以用系统环境代理
                # 如果需要强制用代理获取token，逻辑会复杂些，这里暂时直连
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

    def _send_msg_sync(self, proxy: str | None, token: str, message_body: dict) -> dict | None:
        """
        同步发送消息
        """
        proxies = {"http": proxy, "https": proxy} if proxy else None
        # 使用 Session 复用链接
        with requests.Session() as session:
            if proxies:
                logger.info(f"使用代理: {proxy}")
                session.proxies.update(proxies)
            else:
                logger.info("使用本地IP发送")

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
        loop = asyncio.get_running_loop()

        # 获取 Token (复用 proxy session) 不需要使用代理
        token = self._get_access_token_sync()
        if not token:
            return {"code": 500, "message": "获取token失败"}

        # 转换消息体
        message_body = self._build_message_body(request)

        # 0. 准备测试队列
        candidates = []

        # 1. 优先尝试缓存的代理
        if self.cached_proxy:
             candidates.append(self.cached_proxy)

        # 定义一个内部函数来执行尝试列表
        async def try_candidates(proxy_list, is_full_scan=False):
             nonlocal error_msg
             for i, proxy in enumerate(proxy_list):
                if is_full_scan:
                     logger.info(f"Full Scan Attempt {i+1}/{len(proxy_list)}: {proxy}")

                result = await loop.run_in_executor(None, self._send_msg_sync, proxy, token, message_body)

                if result["code"] == 0:
                    # 成功，更新缓存
                    if proxy != self.cached_proxy:
                        self.cached_proxy = proxy
                        logger.info(f"更新缓存代理为: {proxy}")
                    return result
                else:
                    err = f"Proxy {proxy} failed: {result.get('data')}"
                    # 只有全量扫描时的错误才值得详细记录到最终返回里，避免太长
                    if is_full_scan or len(proxy_list) == 1:
                        error_msg.append(err)
             return None

        error_msg = []

        # 2. 尝试缓存代理
        if candidates:
            res = await try_candidates(candidates)
            if res: return res
            logger.warning("缓存代理失效，开始尝试全量代理")

        # 3. 缓存失效，获取全量代理
        # 注意：不再使用 get_valid_proxies_list 进行检测
        from src.app.proxy import get_all_proxies_from_db
        all_proxies = await get_all_proxies_from_db()

        # 过滤掉已经试过的 cached_proxy (其实不过滤也就重试一次，无所谓，但过滤了更干净)
        retry_proxies = [p for p in all_proxies if p != self.cached_proxy]

        # 加上本地IP作为最后兜底 (user logic: failed -> use all proxies. Usually local is backup)
        # 如果 self.cached_proxy 是 None (之前是本地IP成功)，那么 retry_proxies 就是全量代理。
        # 如果 retry_proxies 里不包含 None，需要加上。
        # 注意: get_all_proxies_from_db 返回的是 url string list. None 代表 Local IP.
        retry_proxies.append(None)

        if self.cached_proxy is None:
             # 如果 cached_proxy 是 None (Local IP)，并且它刚才试过失败了
             # 那么 retry_proxies 最后一个 None 就重复了。
             # 实际上 candidates=[None] 失败了，retry_proxies=[p1, p2, ..., None]
             # 最后一个 None 可以删掉?
             # 或者，既然 Local IP 刚才失败了，再试一次也无妨，或者应该避免。
             # 为简单起见，不刻意去重 None，除非 cached_proxy 确实是 None 且失败了。
             pass

        res = await try_candidates(retry_proxies, is_full_scan=True)
        if res: return res

        logger.error("All attempts failed")
        return {"code": 500, "message": f"所尝试理均失效, {error_msg}"}

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
