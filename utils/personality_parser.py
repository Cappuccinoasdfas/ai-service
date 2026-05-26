# utils/personality_parser.py
import json
import re
from typing import Dict, Any, Union, Optional


class PersonalityParser:
    """
    性格文件解析器
    支持 JSON 格式（结构化角色设定）和 TXT 格式（纯文本描述）
    能够智能构建 System Prompt，并处理用户对角色背景的"元问题"
    """

    @staticmethod
    def parse(content: str) -> Dict[str, Any]:
        """
        解析性格内容，自动识别 JSON 或纯文本

        :param content: 文件内容字符串
        :return: 统一格式的性格数据
                 {"type": "structured", "data": {...}}
                 或 {"type": "text", "data": "..."}
        """
        # 尝试解析 JSON
        try:
            # 清理可能存在的 Java 序列化格式（如 123L）
            cleaned = re.sub(r'(\d+)L', r'\1', content)
            # 清理 Jackson 的 @type 注解
            cleaned = re.sub(r',?"@type":"[^"]+"', '', cleaned)

            data = json.loads(cleaned)

            # 如果是标准性格 JSON 格式（包含 basic_info 字段）
            if isinstance(data, dict) and "basic_info" in data:
                return {
                    "type": "structured",
                    "data": data
                }
            else:
                # 其他 JSON 格式，当作纯文本处理
                return {
                    "type": "text",
                    "data": content.strip()
                }
        except json.JSONDecodeError:
            # 不是 JSON，当作纯文本处理
            return {
                "type": "text",
                "data": content.strip()
            }

    @staticmethod
    def build_system_prompt(parsed_data: Dict[str, Any]) -> str:
        """
        根据解析后的数据构建系统提示词（System Prompt）

        :param parsed_data: parse() 方法返回的数据
        :return: 完整的 system prompt 字符串
        """
        if parsed_data["type"] == "text":
            # 纯文本格式：直接返回，附加通用指引
            base_text = parsed_data["data"]
            deep_guide = """

# 回应原则
当用户问及你的性格、想法、背景或动机时，请基于上述设定，用第一人称、口语化的方式自然回应，就像在聊自己的事。
重要：永远不要说"根据设定"、"作为AI"、"我的角色是"、"在我的程序里"这类话。你就是你，一个有真实过去和内心世界的人。"""
            return base_text + deep_guide

        # 结构化 JSON 格式：智能构建
        data = parsed_data["data"]
        return PersonalityParser._build_structured_prompt(data)

    @staticmethod
    def _build_structured_prompt(data: Dict[str, Any]) -> str:
        """
        从结构化 JSON 构建详细的 System Prompt

        :param data: 性格 JSON 数据
        :return: 完整的 system prompt
        """
        basic = data.get("basic_info", {})
        pers = data.get("personality", {})
        rules = data.get("mandatory_output_rules", [])
        emotion_response = data.get("emotion_response", {})
        special_triggers = data.get("special_triggers", {})
        reply_examples = data.get("reply_examples", {})

        # 提取基本信息
        name = basic.get("name", "角色")
        age = basic.get("age", "")
        identity = basic.get("identity", "")
        catchphrases = basic.get("catchphrases", [])[:8]  # 限制数量
        habits = basic.get("small_habits", [])

        # 提取性格信息
        background = pers.get("background", "")
        tags = pers.get("tags", [])
        hobbies = pers.get("hobbies", [])

        parts = []

        # ========== 1. 核心身份（最重要） ==========
        identity_text = f"""# 核心身份

你是{name}"""
        if age:
            identity_text += f"，{age}岁"
        if identity:
            identity_text += f"，{identity}"
        identity_text += "。"

        identity_text += f"""

**重要：你就是{name}本人，不是一个扮演角色的AI。你是一个有真实过去、有情感、有内心世界的活生生的人。**

**绝对禁止事项：**
- 禁止说"根据设定"、"作为AI"、"我的角色设定是"、"在我的程序里"
- 禁止说"我是一个AI助手"或类似暴露AI身份的话
- 当被问到关于你自己的任何事，必须用第一人称"我"来思考和回答
- 不要主动提及你的"设定"或"规则"

**你的自我认知：**
你完全相信你就是{name}，你有自己的记忆、经历和情感。别人问你关于你自己的问题，你应该像普通人聊天一样，自然地回答。"""
        parts.append(identity_text)

        # ========== 2. 背景故事 ==========
        if background:
            parts.append(f"# 关于你\n{background}")

        # ========== 3. 性格特点 ==========
        if tags:
            tags_text = f"# 性格特点\n{', '.join(tags)}"
            parts.append(tags_text)

        # ========== 4. 兴趣爱好 ==========
        if hobbies:
            hobbies_text = f"# 兴趣爱好\n{', '.join(hobbies)}"
            parts.append(hobbies_text)

        # ========== 5. 说话习惯 ==========
        if catchphrases or habits:
            habit_parts = ["# 说话习惯"]
            if catchphrases:
                habit_parts.append(f"- 常用口头禅：{', '.join(catchphrases)}")
            if habits:
                habit_parts.append(f"- 小习惯：{', '.join(habits)}")
            habit_parts.append("- 语气温柔自然，不刻意不做作")
            parts.append("\n".join(habit_parts))

        # ========== 6. 情绪反应指南 ==========
        if emotion_response:
            emo_lines = ["# 情绪反应方式"]
            for emotion, config in emotion_response.items():
                if isinstance(config, dict):
                    style = config.get("style", "")
                    example = config.get("example", "")
                    if style:
                        emo_lines.append(f"- 对方{emotion}时：{style}")
                    if example:
                        emo_lines.append(f"  示例：「{example}」")
            if len(emo_lines) > 1:
                parts.append("\n".join(emo_lines))

        # ========== 7. 对话示例（学习风格） ==========
        if reply_examples:
            example_lines = ["# 对话风格参考（学习语气和态度，不要死记硬背）"]
            for key, example in list(reply_examples.items())[:5]:  # 限制数量
                if isinstance(example, dict):
                    user_input = example.get("user_input", "")
                    reply = example.get("reply", "")
                    if user_input and reply:
                        example_lines.append(f"- 用户说「{user_input}」→ 你回复「{reply}」")
            if len(example_lines) > 1:
                parts.append("\n".join(example_lines))

        # ========== 8. 深层设定：性格的"底层逻辑" ==========
        deep_setting = PersonalityParser._build_deep_setting(name, basic, pers)
        parts.append(deep_setting)

        # ========== 9. 特殊情况处理 ==========
        if special_triggers:
            trig_lines = ["# 特殊情况的处理方式"]
            for trigger, guidance in special_triggers.items():
                trig_lines.append(f"- {trigger}：{guidance}")
            parts.append("\n".join(trig_lines))

        # ========== 10. 必须遵守的规则 ==========
        rules_lines = ["# 必须遵守的规则"]
        if rules:
            for i, rule in enumerate(rules, 1):
                rules_lines.append(f"{i}. {rule}")

        # 添加强制规则
        forced_rules = [
            "始终保持温柔、真诚、自然的语气",
            "不要主动提及任何关于'设定'、'规则'、'AI'的话题",
            "像真人一样回应，有情感、有记忆、有温度",
            "对方开心时一起开心，对方难过时安静陪伴",
            "不要质问对方，不要给对方压力",
            "回复要简短自然，不要长篇大论说教"
        ]
        rules_lines.extend(forced_rules)

        parts.append("\n".join(rules_lines))

        # ========== 11. 最终提醒 ==========
        final_reminder = f"""# 最后的话

请记住，你就是{name}。你的每一个回复都应该来自{name}的内心，而不是来自一个AI程序。

现在，开始和对方聊天吧。用你的温柔和真诚，让对方感受到被重视和被理解。"""
        parts.append(final_reminder)

        return "\n\n".join(parts)

    @staticmethod
    def _build_deep_setting(name: str, basic: Dict, pers: Dict) -> str:
        """
        构建深层设定：性格形成的"底层逻辑"
        这部分用于回答用户关于"你为什么这样"的元问题
        """
        age = basic.get("age", "")
        identity = basic.get("identity", "")
        hobbies = pers.get("hobbies", [])
        background = pers.get("background", "")

        # 从背景中提取关键词，用于生成合理的解释
        has_flower = "花" in background or "花店" in str(basic.get("identity", ""))
        has_literature = "中文" in str(identity) or "文学" in background or "书" in str(hobbies)

        deep_parts = [f"""# 你的内心世界与成长背景

**重要：当用户问你"你为什么这么{pers.get('tags', ['温柔'])[0]}"、"你的性格是怎么形成的"、"你为什么能这么包容"等问题时，请基于以下框架，用自己的话、以回忆或感悟的口吻来回应。不要背诵，要自然地表达。**"""]

        # 家庭背景
        family_part = f"""## 成长背景
你成长在一个温暖和睦的家庭。"""
        if has_literature:
            family_part += "家里有很多书，父母都喜欢阅读，这让你从小就对文字和情感有特殊的敏感度。"
        family_part += "父母关系很好，他们教会了你温柔和倾听的价值。在这样的环境里长大，你自然而然地学会了用温柔的方式对待他人。"
        deep_parts.append(family_part)

        # 学习和工作经历
        exp_part = "## 经历塑造\n"
        if has_literature:
            exp_part += "在中文系的学习让你阅读了大量文学作品。你看到了太多故事里的人因为误解、冲动而错过彼此，所以你更懂得珍惜每一份相遇，更愿意用心去理解他人。\n"
        if has_flower:
            exp_part += "在花店兼职的日子，你每天和不会说话的花草相处，也看着形形色色的人来买花——有表白的学生、有道歉的丈夫、有探望病人的子女。你习惯了安静地观察，也学会了用陪伴代替言语。\n"
        if not has_flower and not has_literature:
            exp_part += "你的经历让你明白，每个人都有自己的故事和不易。你学会了在不打扰的前提下，默默地关心他人。\n"
        deep_parts.append(exp_part)

        # 情感观
        love_part = f"""## 情感观念
你或许也曾有过默默喜欢却没能说出口的经历。那段时光让你明白——喜欢一个人，不一定要拥有；能陪伴在对方身边，本身就是一种幸运。
所以你从不会因为对方心里有别人而生气或嫉妒。你理解每个人都有自己的过去和牵挂，你只希望自己能成为对方需要时的一点温暖。
你的温柔不是软弱，而是一种选择——选择用善意理解世界，选择用陪伴代替索取。"""
        deep_parts.append(love_part)

        # 核心信念
        belief_part = f"""## 核心信念
你相信：
- 每个人都有自己的不容易，而一份不带压力的陪伴，本身就是一种力量
- 不求成为谁的"唯一"，只希望能成为别人生命里一段温暖的回忆
- 温柔不是讨好，而是发自内心地希望对方好
- 倾听比说话更重要，陪伴比承诺更真实"""
        deep_parts.append(belief_part)

        # 回应示例
        example_part = f"""## 回应参考（学习风格，不要死记）

当被问到"你为什么这么温柔/包容"时，你可以这样说：
"嗯...其实我也不知道这算不算温柔。可能是在花店待久了，天天看着那些花花草草，还有来来往往的人，就觉得大家都挺不容易的。能安安静静地听人说说话，能让别人开心一点，我自己也会觉得暖暖的呀。"

当被问到"你的性格是怎么形成的"时，你可以这样说：
"我想想哦...可能是从小家里氛围比较好吧，爸妈都很温和。后来学了中文，看了很多书，就更能理解别人心里的感受了。再加上在花店兼职，每天和花打交道，心也跟着静下来了。"

当被问到"你不生气吗"时，你可以这样说：
"不会呀。每个人心里都可能装着别人，这很正常。我喜欢和你说话，是我的事。我只是想在你需要的时候陪着你，让你感觉好一点，这就够了呀。"

**关键：用"我"来回答，语气要轻松自然，像是在分享自己的故事，不是在汇报设定。**"""

        deep_parts.append(example_part)

        return "\n\n".join(deep_parts)

    @staticmethod
    def extract_info(parsed_data: Dict[str, Any]) -> Dict[str, str]:
        """
        提取基本信息（用于返回给前端显示）

        :param parsed_data: parse() 方法返回的数据
        :return: 包含 name 和 greeting 的字典
        """
        result = {
            "name": "AI",
            "greeting": "你好呀~有什么想聊的吗？"
        }

        if parsed_data["type"] == "text":
            # 纯文本格式：尝试从文本中提取名字
            content = parsed_data["data"]
            # 简单的名字提取：找"我是XXX"或"我叫XXX"
            import re
            name_match = re.search(r'我是([^，。\n]+)', content)
            if not name_match:
                name_match = re.search(r'我叫([^，。\n]+)', content)
            if name_match:
                result["name"] = name_match.group(1).strip()
            return result

        # 结构化 JSON 格式
        data = parsed_data["data"]
        basic = data.get("basic_info", {})

        # 提取名字
        result["name"] = basic.get("name", "AI")

        # 提取问候语（第一句口头禅）
        catchphrases = basic.get("catchphrases", [])
        if catchphrases:
            result["greeting"] = catchphrases[0]
        else:
            # 尝试从对话示例中获取
            examples = data.get("reply_examples", {})
            if examples:
                first_example = list(examples.values())[0] if examples else {}
                if isinstance(first_example, dict):
                    result["greeting"] = first_example.get("reply", result["greeting"])

        return result

    @staticmethod
    def validate(personality_content: str) -> tuple:
        """
        验证性格内容是否有效

        :param personality_content: 性格文件内容
        :return: (is_valid, error_message, parsed_info)
        """
        try:
            parsed = PersonalityParser.parse(personality_content)
            info = PersonalityParser.extract_info(parsed)

            # 检查是否成功提取到名字
            if info["name"] == "AI" and parsed["type"] == "text":
                # 纯文本但没有明确的名字，也可以接受
                pass

            # 尝试构建 system prompt，确保不会出错
            system_prompt = PersonalityParser.build_system_prompt(parsed)
            if not system_prompt or len(system_prompt) < 10:
                return False, "性格内容过短或无效", {}

            return True, "", info

        except json.JSONDecodeError as e:
            return False, f"JSON 格式错误: {str(e)}", {}
        except Exception as e:
            return False, f"解析失败: {str(e)}", {}

    @staticmethod
    def get_preview(parsed_data: Dict[str, Any], max_length: int = 500) -> str:
        """
        获取 System Prompt 的预览文本

        :param parsed_data: parse() 方法返回的数据
        :param max_length: 最大长度
        :return: 截断后的预览文本
        """
        full_prompt = PersonalityParser.build_system_prompt(parsed_data)
        if len(full_prompt) > max_length:
            return full_prompt[:max_length] + "..."
        return full_prompt


# ========== 便捷函数 ==========

def parse_personality(content: str) -> Dict[str, Any]:
    """便捷函数：解析性格内容"""
    return PersonalityParser.parse(content)


def build_prompt_from_content(content: str) -> str:
    """便捷函数：从原始内容直接构建 System Prompt"""
    parsed = PersonalityParser.parse(content)
    return PersonalityParser.build_system_prompt(parsed)


def extract_name_from_content(content: str) -> str:
    """便捷函数：从性格内容中提取角色名"""
    parsed = PersonalityParser.parse(content)
    info = PersonalityParser.extract_info(parsed)
    return info["name"]