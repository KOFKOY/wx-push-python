from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # 企业微信配置
    CORP_ID: str = ""
    CORP_SECRET: str = ""
    AGENT_ID: str = ""
    # 暂时不需要独立的 TOKEN 配置，因为 access_token 是动态获取的。
    # 如果需求文档里的 "接口的token" 指的是我们要开发的这个服务的鉴权token，那需要加一个。
    # 需求文档说 "接口的token"，这可能指企业微信的，也可能指本服务的。
    # "2. 获取 access_token ... 获取token" -> 这是企业微信的 token。
    # "企业微信配置... 还有接口的token" -> 这里有点歧义。
    # 结合上下文 "企业微信的corpid和corpsecret 应用的agent-id 还有接口的token"，这四个并列，可能是指企业微信应用的 Token (用于接收消息的回调)？
    # 或者是指本服务的安全 Token？
    # 既然是 "发送消息"，通常只需要 CorpID, Secret, AgentID。
    # 为了保险，先加上一个 SERVICE_TOKEN 用于本服务鉴权（如果有需要），或者如果是指企业微信的，暂且留着。
    # 这里的 "接口的token" 可能是指 `Authorization` header 用的 token 或者是企业微信 API 需要的某个 token？
    # 通常企业微信发消息只需要 access_token (由 corp_id + secret 换取)。
    # 让我们假设 "接口的token" 是指为了保护我们自己这个服务的 API 用的 token。

    # 数据库配置
    DB_HOST: str = ""
    DB_PORT: int = 0
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""

    # 应用配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # 代理检测 URL
    PROXY_CHECK_URL: str = "https://httpbin.org/ip"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache
def get_settings():
    return Settings()
