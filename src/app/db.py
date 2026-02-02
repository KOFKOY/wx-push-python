import asyncpg
from contextlib import asynccontextmanager
from src.app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    database=settings.DB_NAME,
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                )
            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                # 即使数据库连接失败，应用也应该启动，因为可以使用本地IP发送
                self.pool = None

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def fetch_all(self, query: str, *args):
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    # 批量插入
    async def execute_many(self, query: str, args_list: list[tuple]):
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(query, args_list)

db = Database()