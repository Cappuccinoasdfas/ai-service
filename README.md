# ai-service

## 🤖 AI-Service

基于 **FastAPI + Ollama** 的AI服务，提供统一接口调用本地大模型。

### 核心能力

- 💬 **智能聊天**：多轮对话、上下文记忆、性格定制
- 🔍 **内容审核**：敏感词过滤、安全检测
- 🎨 **文本生成**：摘要、扩写、翻译等

### 技术栈

| 技术 | 说明 |
|------|------|
| Python 3.10+ | 运行环境 |
| FastAPI | Web框架 |
| Ollama | 本地大模型运行工具 |
| Qwen2.5 | 轻量级模型 |
| Redis | 性格配置 + 聊天记录缓存 |

---

## 🚀 快速开始

### 1. 启动依赖服务

```bash
# Redis（必须）
redis-server

# Ollama + 拉取模型（必须）
ollama pull qwen2.5:1.5b
```
## 2. 启动AI服务
python main.py
服务默认运行在 http://localhost:5000/chat/stream

📡 API接口
智能聊天（流式输出）
接口： POST /chat/stream

请求示例：

json
{
    "question": "你吃东西了吗",
    "user_id": 2
}

响应： SSE流式输出（打字机效果）

性格配置加载
AI服务会从Redis中读取用户的性格配置和聊天记录：

Redis Key	说明
personality:user:{userId}	用户性格配置（系统默认userId=0）
ChatAI:user:{userId}:session:{sessionId}	用户聊天历史记录
💡 注意：调用AI接口前，需由Java后端将性格配置和聊天记录预加载到Redis中。

🔗 与Java后端集成
性格配置加载
java
// Java后端调用此方法，将用户性格加载到Redis
public void loadPersonalityToRedis(Long userId) {
    String key = "personality:user:" + userId;
    // 查询用户性格配置，写入Redis，TTL默认24小时
}
聊天记录同步
java
// 用户发送消息时，同步存储到Redis
String key = String.format("ChatAI:user:%s:session:%s", userId, sessionId);
stringRedisTemplate.opsForList().rightPush(key, JSON.toJSONString(msg));
完整调用流程
text
1. Java后端 → 加载性格配置到Redis
2. Java后端 → 加载聊天记录到Redis
3. Java后端 → 调用 /chat/stream 接口（传入user_id + question）
4. AI服务 → 从Redis读取性格 + 上下文
5. AI服务 → 调用Ollama生成回复
6. AI服务 → SSE流式返回

⚙️ 配置说明
配置项	默认值	说明
REDIS_HOST	localhost	Redis地址
REDIS_PORT	6379	Redis端口
OLLAMA_HOST	http://localhost:11434	Ollama服务地址
MODEL_NAME	qwen2.5:1.5b	使用的模型
text
