# services/ai_service.py
import json
from typing import Dict, Any, Optional
from flask import Response, stream_with_context
import logging

logger = logging.getLogger(__name__)

from models.ai_model import ai_model
from models.redis_manager import redis_client
from utils.personality_parser import PersonalityParser


class AIService:
    """AI 服务层 - 仅流式对话"""

    @staticmethod
    def save_user(user_id, username):
        """保存用户信息"""
        redis_client.hset(f"user:{user_id}", "username", username)

    @staticmethod
    def get_username(user_id):
        """获取用户名"""
        return redis_client.hget(f"user:{user_id}", "username")

    @staticmethod
    def save_personality(user_id: str, personality_content: str) -> bool:
        """保存用户性格到 Redis"""
        try:
            parsed = PersonalityParser.parse(personality_content)
            cache_key = f"personality:user:{user_id}"
            redis_client.set(cache_key, personality_content)
            return True
        except Exception as e:
            logger.error(f"Failed to save personality: {e}")
            return False

    @staticmethod
    def get_personality_from_redis(user_id: str) -> Optional[str]:
        """从 Redis 获取原始性格内容"""
        cache_key = f"personality:user:{user_id}"
        return redis_client.get(cache_key)

    @staticmethod
    def get_chat_history(user_id: str, session_id: str) -> str:
        """从 Redis List 获取对话历史"""
        try:
            chat_key = f"ChatAI:user:{user_id}:session:{session_id}"
            messages = redis_client.lrange(chat_key, 0, -1)

            if not messages:
                logger.info(f"未找到聊天记录: user={user_id}, session={session_id}")
                return ""

            history_parts = []
            for msg_json in messages:
                try:
                    record = json.loads(msg_json)
                    role = record.get('role', '')
                    content = record.get('content', '')
                    create_time = record.get('createTime', '')
                    time_str = ""
                    if create_time:
                        time_str = f"[{create_time}] "
                    if role and content:
                        history_parts.append(f"{time_str}用户: {role}\nAI: {content}")
                except json.JSONDecodeError as e:
                    logger.error(f"解析历史记录失败: {e}")
                    continue

            history_str = "\n".join(history_parts)
            logger.info(f"读取到 {len(history_parts)} 条聊天记录")
            return history_str

        except Exception as e:
            logger.error(f"读取聊天记录失败: {e}")
            return ""

    @staticmethod
    def get_personality(user_id: str) -> str:
        """从 Redis 获取性格设定"""
        try:
            personality_key = f"personality:user:{user_id}"
            personality_json_str = redis_client.get(personality_key)

            if not personality_json_str:
                logger.warning(f"未找到性格设定: user={user_id}")
                return ""

            parsed = PersonalityParser.parse(personality_json_str)
            system_prompt = PersonalityParser.build_system_prompt(parsed)

            logger.info(f"成功加载性格文件，system_prompt 长度: {len(system_prompt)}")
            return system_prompt

        except Exception as e:
            logger.error(f"读取性格文件失败: {e}")
            return ""

    @staticmethod
    def process_chat_request_stream(request_data: Optional[Dict[str, Any]]):
        """
        流式对话接口 - 唯一的对话方式

        :param request_data: 请求数据
        :return: Flask Response 对象（SSE 格式）
        """
        # 1. 验证数据
        if not request_data:
            def error_gen():
                yield f"data: {json.dumps({'type': 'error', 'data': '请提供 JSON 数据'}, ensure_ascii=False)}\n\n"

            return Response(stream_with_context(error_gen()), mimetype='text/event-stream')

        question = request_data.get('question', '')
        if not question:
            def error_gen():
                yield f"data: {json.dumps({'type': 'error', 'data': '请提供 question 字段'}, ensure_ascii=False)}\n\n"

            return Response(stream_with_context(error_gen()), mimetype='text/event-stream')

        # 2. 获取用户信息
        user_id = request_data.get('user_id')
        session_id = request_data.get('session_id')

        system_prompt = ""
        chat_history_str = ""

        if user_id:
            system_prompt = AIService.get_personality(user_id)
            if session_id:
                chat_history_str = AIService.get_chat_history(user_id, session_id)

        # 3. 构建完整提示词
        if chat_history_str:
            full_prompt = f"以下是之前的对话记录，请记住这些内容并根据上下文回答：\n\n{chat_history_str}\n\n现在用户说：{question}\n\n请以符合性格的方式回答。"
        else:
            full_prompt = question

        # 4. 流式生成
        options = {
            'temperature': request_data.get('temperature', 0.85),
            'num_predict': request_data.get('num_predict', 256)
        }

        def generate():
            try:
                logger.info(f"开始流式生成: user={user_id}, session={session_id}")

                for token in ai_model.generate_stream(
                        prompt=full_prompt,
                        system_prompt=system_prompt,
                        **options
                ):
                    yield f"data: {json.dumps({'type': 'token', 'data': token}, ensure_ascii=False)}\n\n"

                # 发送完成标记
                logger.info(f"流式生成完成: user={user_id}, session={session_id}")
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"流式生成异常: {e}")
                yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )