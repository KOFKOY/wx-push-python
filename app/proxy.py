
import logging
from app.db import db
from app.config import get_settings

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
        logger.info(f'获取到数据库代理数量：{len(proxies)}')
        return proxies
    except Exception as e:
        logger.error(f"Failed to fetch proxies from DB: {e}")
        return []

import requests
import asyncio
import re

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
        logger.error(f"代理不可用:{proxy_url}")
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

async def check_add_proxy(content: str) -> int:
    """
    解析文本中的代理并入库
    格式: protocol://ip:port ...
    例如: socks5://176.181.163.79:8889
    """
    logger.info("开始解析并检测代理...")
    added_count = 0

    # 正则提取 protocol, ip, port
    # 忽略行中其他信息
    pattern = re.compile(r'(?P<protocol>\w+)://(?P<ip>[\d\.]+):(?P<port>\d+)')

    tasks = []
    proxy_meta_list = []

    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = pattern.search(line)
        if match:
            protocol = match.group('protocol')
            ip = match.group('ip')
            port = match.group('port')

            # 构造检测用的 URL
            # 如果是 socks5, 使用 socks5h 进行检测 (支持远程 DNS 解析)
            check_protocol = protocol
            if protocol == 'socks5':
                check_protocol = 'socks5h'

            proxy_url = f"{check_protocol}://{ip}:{port}"

            # 使用 check_proxy (它内部会调用 _check_proxy_sync)
            tasks.append(check_proxy(proxy_url))
            proxy_meta_list.append((protocol, ip, port))

    if not tasks:
        logger.warning("未解析到任何符合格式的代理")
        return 0

    # 并发检测
    results = await asyncio.gather(*tasks)

    insert_data = []

    for i, is_valid in enumerate(results):
        if is_valid:
            protocol, ip, port, = proxy_meta_list[i]
            # 准备入库数据: ip, port, protocol, user, pw, status
            # user, pw 默认为空字符串
            insert_data.append((ip, int(port), protocol, '', '', 0))

    if insert_data:
        # 批量插入
        query = """
            INSERT INTO proxies (ip, port, protocol, "user", pw, status)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        try:
             await db.execute_many(query, insert_data)
             added_count = len(insert_data)
             logger.info(f"成功入库 {added_count} 个代理")
        except Exception as e:
            logger.error(f"入库失败: {e}")
    else:
        logger.info("没有可用代理需要入库")

    return added_count

async def get_raw_proxies_from_db():
    """
    获取数据库中所有代理原始记录 (包含 ID 和 Status)
    """
    try:
        return await db.fetch_all("SELECT * FROM proxies")
    except Exception as e:
        logger.error(f"Failed to fetch raw proxies: {e}")
        return []

async def check_and_update_all_proxies() -> dict:
    """
    查询全表数据，检测代理可用性。
    如果检测状态与数据库状态不一致，则更新数据库状态和创建时间。
    """
    logger.info("开始全量检测代理并更新状态...")
    rows = await get_raw_proxies_from_db()
    if not rows:
        return {"total": 0, "updated": 0}

    tasks = []
    proxy_meta_list = []

    for row in rows:
        ip = row.get('ip') or row.get('host')
        port = row.get('port')
        protocol = row.get('protocol', 'http')
        user = row.get('user')
        password = row.get('pw')

        check_protocol = protocol
        if protocol == 'socks5':
            check_protocol = 'socks5h'

        if user and password:
            proxy_url = f"{check_protocol}://{user}:{password}@{ip}:{port}"
        else:
            proxy_url = f"{check_protocol}://{ip}:{port}"

        tasks.append(check_proxy(proxy_url))
        proxy_meta_list.append(row)

    # 并发检测
    results = await asyncio.gather(*tasks)

    updates = []

    for i, is_valid in enumerate(results):
        row = proxy_meta_list[i]
        current_status = row['status']
        # 数据库中 status: 1=可用, 0=不可用
        new_status = 1 if is_valid else 0

        # 状态不一致则更新
        if current_status != new_status:
            updates.append((new_status, row['id']))

    if updates:
        query = "UPDATE proxies SET status = $1, created_at = CURRENT_TIMESTAMP WHERE id = $2"
        try:
            await db.execute_many(query, updates)
            logger.info(f"Updated {len(updates)} proxies")
        except Exception as e:
            logger.error(f"Failed to update proxies: {e}")

    return {"total": len(rows), "updated": len(updates)}
