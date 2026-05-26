# redis_manager.py
import redis

# 连接池
_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    password=None,
    db=0,
    decode_responses=True,
    max_connections=10
)

# 全局客户端（单例）
redis_client = redis.Redis(connection_pool=_pool)

# 测试连接
redis_client.ping()