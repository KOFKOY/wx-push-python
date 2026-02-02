from pydantic import BaseModel, Field
from enum import Enum

class MessageType(str, Enum):
    TEXT_CARD = "TEXT_CARD"
    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"

class PushRequest(BaseModel):
    target: str = Field(..., description="接收人，多个用|分隔")
    type: MessageType = Field(default=MessageType.TEXT_CARD, description="消息类型")
    title: str = Field(..., description="消息标题")
    content: str = Field(..., description="消息内容")
    url: str = Field(..., description="点击消息跳转的url")

class PushResponse(BaseModel):
    code: int
    message: str
    data: dict | None = None
