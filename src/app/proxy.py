
import logging
from src.app.db import db
from src.app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def get_all_proxies_from_db():
    """
    从数据库获取所有代理
    """
    try:
        rows = await db.fetch_all("SELECT * FROM proxies WHERE status = 1")
        proxies = []
        ips = []
        ip_ports = []
        for row in rows:
            ip = row.get('ip') or row.get('host')
            ips.append(ip)
            port = row.get('port')
            ip_ports.append(f"{ip}:{port}")
            protocol = row.get('protocol', 'http')
            #添加用户密码
            user = row.get('user')
            password = row.get('pw')
            #如果是socks5协议 ,使用socks5h
            if protocol == 'socks5':
                protocol = 'socks5h'
            if ip and port:
                if user and password:
                    proxies.append(f"{protocol}://{user}:{password}@{ip}:{port}")
                else:
                    proxies.append(f"{protocol}://{ip}:{port}")
        # print(";".join(ips))
        return proxies
    except Exception as e:
        logger.error(f"Failed to fetch proxies from DB: {e}")
        return []

import requests
import asyncio

async def check_proxy(proxy_url: str) -> bool:
    """
    测试代理是否可用 (异步包装同步 requests)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _check_proxy_sync, proxy_url)

def _check_proxy_sync(proxy_url: str) -> bool:
    try:
        proxies = {"http": proxy_url, "https": proxy_url}
        resp = requests.get(settings.PROXY_CHECK_URL, proxies=proxies, timeout=5.0)
        if resp.status_code == 200:
            return True
    except Exception as e:
        logger.error(f"Failed to check proxy {proxy_url}: {e}")
    return False

async def get_valid_proxies_list(limit: int = 5) -> list[str]:
    """
    获取多个可用的代理列表，用于重试。
    """
    proxies = await get_all_proxies_from_db()
    if not proxies:
        return []

    valid_proxies = []
    for proxy in proxies:
        if len(valid_proxies) >= limit:
            break
        if await check_proxy(proxy):
            valid_proxies.append(proxy)

    return valid_proxies
