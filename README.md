# 企业微信消息推送服务

一个最简版企业微信通知服务，仅保留消息发送能力，不依赖数据库和代理。

## 功能

- 支持 `TEXT_CARD`、`TEXT` 两种消息类型
- 自动获取并缓存企业微信 `access_token`
- 仅通过企业微信官方接口直连发送消息

## 运行要求

- Python 3.10+
- 企业微信应用配置：`CORP_ID`、`CORP_SECRET`、`AGENT_ID`

## 本地启动

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 11180
```

`.env` 示例：

```ini
CORP_ID=your_corp_id
CORP_SECRET=your_corp_secret
AGENT_ID=your_agent_id
```

## Docker 启动

```bash
docker-compose up -d --build
```

## API

### POST /push

请求体：

```json
{
  "target": "UserID1|UserID2",
  "type": "TEXT_CARD",
  "title": "测试消息",
  "content": "这是一条测试消息内容",
  "url": "https://example.com"
}
```
