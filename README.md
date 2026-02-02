# 企业微信消息推送服务

基于 FastAPI 和 AsyncPG 构建的企业微信消息推送服务，支持从 PostgreSQL 代理池中获取代理进行发送，具备自动重试和 IP 切换功能。

## 功能特性

- **消息类型支持**: 支持文本卡片 (TextCard)、文本 (Text) 等多种消息格式。
- **代理池集成**: 从 PostgreSQL 数据库读取代理，自动检测可用性。
- **智能重试**: 发送失败或 IP 受限时，自动切换代理重试 (默认 3 次)，全部失败后降级使用本地 IP。
- **配置管理**: 基于环境变量的配置管理。
- **容器化**: 提供完整的 Docker Compose 部署方案。

## 快速开始

### 1. 环境准备

- Python 3.10+
- PostgreSQL
- Docker & Docker Compose (可选)

### 2. 本地运行

安装依赖:
```bash
# 使用 uv (推荐)
uv sync

# 或者使用 pip
pip install .
```

配置环境变量 (创建 `.env` 文件):
```ini
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=proxy_pool

CORP_ID=your_corp_id
CORP_SECRET=your_corp_secret
AGENT_ID=your_agent_id
```

启动服务:
```bash
uvicorn src.app.main:app --reload
```

### 3. Docker 部署

修改 `docker-compose.yml` 或创建 `.env` 文件配置环境变量，特别是数据库连接信息:

```bash
DB_HOST=your_db_host
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

CORP_ID=your_corp_id
CORP_SECRET=your_corp_secret
AGENT_ID=your_agent_id
```

构建并启动服务:

```bash
docker-compose up -d --build
```

服务将在宿主机的 `http://localhost:19007` 启动 (映射到容器端口 8000)。
注意：此部署方案不包含数据库容器，请确保外部 PostgreSQL 数据库可用并已初始化。

## API 接口

### 发送消息

**POST** `/push`

请求体示例:

```json
{
  "target": "WangShuaiJie",
  "type": "TEXT_CARD",
  "title": "测试消息",
  "content": "这是一条测试消息内容",
  "url": "http://example.com"
}
```

响应示例:

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```
