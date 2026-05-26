# models/ai_model.py
import requests
import logging
import json
from typing import Generator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIModel:
    """
    AI 模型封装类 - 单例模式
    支持每次请求动态传入 system prompt
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model="qwen2.5:7b", base_url="http://localhost:11434"):
        if not self._initialized:
            self.model = model
            self.base_url = base_url
            self._check_ollama_status()
            self._warm_up()
            self._initialized = True
            logger.info(f"AI Model initialized: {model}")

    def _check_ollama_status(self):
        """检查 Ollama 服务状态"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                logger.info(f"Available models: {model_names}")
        except Exception as e:
            logger.warning(f"Cannot connect to Ollama: {e}")

    def _warm_up(self):
        """预热模型"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "",
                    "keep_alive": -1
                },
                timeout=10
            )
            logger.info(f"Model {self.model} warmed up successfully")
        except Exception as e:
            logger.warning(f"Model warm-up failed: {e}")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """
        生成回复 - 非流式（保留原方法）

        :param prompt: 用户输入
        :param system_prompt: 系统提示词（性格设定）
        :param kwargs: 其他参数
        :return: AI 回复
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "keep_alive": -1,
            "options": {
                "num_predict": kwargs.get('num_predict', 256),
                "temperature": kwargs.get('temperature', 0.85),
                "top_p": kwargs.get('top_p', 0.9),
                "top_k": kwargs.get('top_k', 40),
                "repeat_penalty": kwargs.get('repeat_penalty', 1.1),
                "seed": kwargs.get('seed', 0),
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=kwargs.get('timeout', 120)
            )
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.Timeout:
            logger.error("AI service timeout")
            raise Exception("AI 服务响应超时")
        except requests.exceptions.ConnectionError:
            logger.error("AI service connection failed")
            raise Exception("无法连接到 AI 服务")
        except Exception as e:
            logger.error(f"AI service error: {e}")
            raise Exception(f"AI 服务出错: {str(e)}")

    def generate_stream(self, prompt: str, system_prompt: str = "", **kwargs) -> Generator[str, None, None]:
        """
        流式生成回复 - 逐 token 返回

        :param prompt: 用户输入
        :param system_prompt: 系统提示词（性格设定）
        :param kwargs: 其他参数
        :yield: 逐个 token
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": True,  # 开启流式
            "keep_alive": -1,
            "options": {
                "num_predict": kwargs.get('num_predict', 1024),
                "temperature": kwargs.get('temperature', 0.85),
                "top_p": kwargs.get('top_p', 0.9),
                "top_k": kwargs.get('top_k', 40),
                "repeat_penalty": kwargs.get('repeat_penalty', 1.1),
                "seed": kwargs.get('seed', 0),
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,  # 开启流式响应
                timeout=kwargs.get('timeout', 120)
            )

            response.encoding = 'utf-8'

            # 逐行读取 NDJSON 格式的响应
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        done = data.get("done", False)

                        if token:
                            yield token

                        if done:
                            break

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON line: {line}, error: {e}")
                        continue

        except requests.exceptions.Timeout:
            logger.error("AI service timeout")
            yield "[ERROR] AI 服务响应超时"
        except requests.exceptions.ConnectionError:
            logger.error("AI service connection failed")
            yield "[ERROR] 无法连接到 AI 服务"
        except Exception as e:
            logger.error(f"AI service error: {e}")
            yield f"[ERROR] AI 服务出错: {str(e)}"


# 全局模型实例
ai_model = AIModel()