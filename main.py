from flask import Flask, request, Response
from services.ai_service import AIService
import time

app = Flask(__name__)


@app.route('/chat', methods=['POST'])
def chat():
    """
    聊天接口 - 非流式（保留原接口）
    """
    if not request.is_json:
        from utils.response import ApiResponse
        return ApiResponse.error("请求格式错误，请使用 JSON 格式", 400)

    request_data = request.get_json()
    return AIService.process_chat_request(request_data)


@app.route('/chat/stream', methods=['POST'])
def chat_stream():
    """
    聊天接口 - 流式输出（新增）
    返回 SSE 格式的流式响应
    """
    if not request.is_json:
        def error_gen():
            import json
            yield f"data: {json.dumps({'error': '请求格式错误，请使用 JSON 格式'})}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')

    request_data = request.get_json()
    return AIService.process_chat_request_stream(request_data)


# ========== 未来扩展接口示例 ==========

@app.route('/image/generate', methods=['POST'])
def generate_image():
    """图像生成接口（未来扩展）"""
    if not request.is_json:
        from utils.response import ApiResponse
        return ApiResponse.error("请求格式错误，请使用 JSON 格式", 400)

    request_data = request.get_json()
    return AIService.process_image_request(request_data)


@app.route('/translate', methods=['POST'])
def translate():
    """翻译接口（未来扩展）"""
    if not request.is_json:
        from utils.response import ApiResponse
        return ApiResponse.error("请求格式错误，请使用 JSON 格式", 400)

    request_data = request.get_json()
    return AIService.process_translation_request(request_data)


def warm_up_model():
    """启动时预热模型"""
    from models.ai_model import ai_model
    print("正在加载 AI 模型，请稍候...")
    start = time.time()

    try:
        # 发送一条极短的预热消息，强制模型加载到显存
        ai_model.generate("你好", num_predict=5, temperature=0.5)
        elapsed = time.time() - start
        print(f"模型加载完成，耗时 {elapsed:.1f} 秒")
        return True
    except Exception as e:
        print(f"模型加载失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("AI 服务启动中...")
    print("=" * 50)

    # 启动时预热模型
    warm_up_model()

    print("\n" + "=" * 50)
    print("AI 服务启动在 http://localhost:5000")
    print("\n可用接口：")
    print("  POST /chat - 聊天接口")
    print("  POST /image/generate - 图像生成接口（预留）")
    print("  POST /translate - 翻译接口（预留）")
    print("\n测试命令：")
    print('  curl -X POST http://localhost:5000/chat \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"question": "你好"}\'')
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

