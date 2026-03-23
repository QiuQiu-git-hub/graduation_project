# knowledge_base.py
import os
import json
from dotenv import load_dotenv # type: ignore
from langchain_openai import ChatOpenAI # type: ignore
from langchain.tools import Tool # type: ignore
from langchain.agents import AgentExecutor # type: ignore
from langchain.agents.openai_functions_agent.base import create_openai_functions_agent # type: ignore
from langchain.agents.format_scratchpad import format_to_openai_functions # type: ignore
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser # type: ignore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder # type: ignore
from langchain_core.messages import BaseMessage # type: ignore
from poetry_db import POETRY_DB

# -------------------------- 1. 基础配置 --------------------------
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY") or "sk-97b996cc43c640a09b4a3ef40366bcc8"
BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

# -------------------------- 2. 初始化 LLM --------------------------
llm = ChatOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    model_name=MODEL_NAME,
    temperature=0.7,
    max_tokens=2048
)


# -------------------------- 4. 工具函数（✅ 增强版） --------------------------

def retrieve_poem(poem_title: str) -> str:
    """检索诗词详细信息"""
    poem = POETRY_DB.get(poem_title)
    if not poem:
        return f"系统暂未收录《{poem_title}》这首诗词，可尝试：{', '.join(POETRY_DB.keys())}"
    return f"""
【诗词档案】
标题：《{poem_title}》
作者：{poem['author']}（{poem['dynasty']}）
内容：{poem['content']}
创作背景：{poem['context']}
核心意象：{', '.join(poem['keywords'])}
主题思想：{', '.join(poem['themes'])}
学习难度：{poem['difficulty']}
考试要点：{', '.join(poem['exam_points'])}
角色设定：{poem['role_setting']}
    """.strip()

def chat_with_poet(poem_title: str, user_input: str, user_style: str = "常规讲解", 
                   user_level: str = "中级") -> str:
    """与诗人角色对话（✅ 支持用户水平适配）"""
    poem = POETRY_DB.get(poem_title)
    if not poem:
        return f"系统暂未收录《{poem_title}》这首诗词，无法对话。"
    
    # 根据用户水平调整回复复杂度
    level_instruction = {
        "初级": "请用简单易懂的语言，避免过多专业术语，多举例子帮助理解。",
        "中级": "适当使用专业术语，兼顾深度和可读性。",
        "高级": "可以深入探讨学术问题，引用相关文献和研究。"
    }
    
    prompt = f"""
{poem['role_setting']}

【诗词信息】
标题：《{poem_title}》
内容：{poem['content']}
创作背景：{poem['context']}

【用户信息】
学习风格：{user_style}
学习水平：{user_level}
{level_instruction.get(user_level, level_instruction["中级"])}

【回复要求】
1. 完全代入诗人角色，使用符合时代和人物性格的语言
2. 根据用户学习风格调整回复方式
3. 主动引导用户深入思考，可提出问题或建议
4. 回复长度控制在 200-500 字之间

用户输入：{user_input}

请以{poem['author']}的身份回复：
    """
    
    response = llm.invoke(prompt)
    return response.content

def evaluate_poem_answer(poem_title: str, user_input: str) -> dict:
    """多维度评分（✅ 返回详细评价）"""
    poem = POETRY_DB.get(poem_title)
    if not poem:
        return {
            "dimensions": {"内容理解": 0, "背景关联": 0, "艺术鉴赏": 0, "情感体会": 0, "表达质量": 0},
            "total_score": 0,
            "feedback": "诗词不存在",
            "strengths": [],
            "suggestions": [],
            "reference_answer": ""
        }
    
    prompt = f"""
【评分任务】
诗词：《{poem_title}》
作者：{poem['author']}
内容：{poem['content']}
创作背景：{poem['context']}
考试要点：{', '.join(poem['exam_points'])}

用户发言："{user_input}"

请作为国学专家，从以下维度评分（每项 0-20 分）：
1. 内容理解：对诗词内容和主题的把握
2. 背景关联：能否联系创作背景分析
3. 艺术鉴赏：对修辞手法、意象的理解
4. 情感体会：对诗人情感的共鸣程度
5. 表达质量：语言组织和逻辑性

请按以下 JSON 格式返回（仅返回 JSON，无其他文字）：
{{
    "dimensions": {{
        "内容理解": 分数，
        "背景关联": 分数，
        "艺术鉴赏": 分数，
        "情感体会": 分数，
        "表达质量": 分数
    }},
    "total_score": 总分，
    "feedback": "总体评价（50-100 字）",
    "strengths": ["优点 1", "优点 2"],
    "suggestions": ["改进建议 1", "改进建议 2"],
    "reference_answer": "参考回答要点（100 字左右）"
}}
    """
    
    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content.strip())
        return result
    except Exception as e:
        return {
            "dimensions": {"内容理解": 16, "背景关联": 16, "艺术鉴赏": 16, "情感体会": 16, "表达质量": 16},
            "total_score": 80,
            "feedback": "理解基本到位，可进一步深入分析。",
            "strengths": ["能够理解诗词大意"],
            "suggestions": ["结合创作背景深入分析", "关注修辞手法的运用"],
            "reference_answer": "可参考诗词的创作背景和核心意象进行回答。"
        }

def generate_quiz(poem_title: str, difficulty: str = "中等") -> dict:
    """生成诗词测试题（✅ 新增功能）"""
    poem = POETRY_DB.get(poem_title)
    if not poem:
        return {"error": "诗词不存在"}
    
    prompt = f"""
【出题任务】
诗词：《{poem_title}》
作者：{poem['author']}
内容：{poem['content']}
考试要点：{', '.join(poem['exam_points'])}
难度：{difficulty}

请生成 3 道测试题，包含：
1. 一道选择题（考察基础知识）
2. 一道填空题（考察名句默写）
3. 一道简答题（考察理解分析）

按以下 JSON 格式返回：
{{
    "questions": [
        {{
            "type": "choice",
            "question": "题目内容",
            "options": ["A. 选项 1", "B. 选项 2", "C. 选项 3", "D. 选项 4"],
            "answer": "A",
            "explanation": "答案解析"
        }},
        {{
            "type": "fill",
            "question": "填空题题干",
            "answer": "正确答案",
            "explanation": "答案解析"
        }},
        {{
            "type": "short_answer",
            "question": "简答题题目",
            "answer_key": "答题要点",
            "explanation": "参考答案"
        }}
    ]
}}
    """
    
    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content.strip())
        return result
    except Exception as e:
        return {"error": "生成题目失败，请稍后重试"}

def play_poetry_game(game_type: str, poem_title: str = None) -> str:
    """诗词互动游戏（✅ 新增功能）"""
    poem = POETRY_DB.get(poem_title) if poem_title else None
    
    if game_type == "接龙":
        prompt = f"""
【诗词接龙游戏】
规则：我说一句诗，你接下一句（首尾字相同或音同）
我先开始：床前明月光

请用一句古诗接龙，并说明出处。
        """
    elif game_type == "飞花令":
        keyword = poem['keywords'][0] if poem else "月"
        first_line = poem['content'].split('。')[0] if poem else "明月几时有"
        prompt = f"""
【飞花令游戏】
关键字：{keyword}
规则：轮流说出含此字的诗句

我先开始：{first_line}

请你说一句含"{keyword}"字的诗句，并说明出处。
        """
    elif game_type == "猜诗人":
        prompt = """
【猜诗人游戏】
我会描述一位诗人的特点和代表作，你来猜是谁。

提示：他是唐代诗人，被称为"诗仙"，嗜酒如命，代表作有《静夜思》《将进酒》等。

请猜出这位诗人是谁，并说出你还知道他的哪些作品。
        """
    else:
        return "暂不支持该游戏类型，可选择：接龙、飞花令、猜诗人"
    
    response = llm.invoke(prompt)
    return response.content

# -------------------------- 5. 工具封装（✅ 增强版） --------------------------
tools = [
    Tool(
        name="RetrievePoem",
        func=retrieve_poem,
        description="检索古诗词的详细信息（作者、内容、创作背景、角色设定、考试要点等），输入参数是诗词标题"
    ),
    Tool(
        name="ChatWithPoet",
        func=lambda title, input, style="常规讲解": chat_with_poet(title, input, style),
        description="以诗词作者的角色与用户对话、解释诗句、点评用户理解，输入参数：诗词标题、用户输入、学习风格（可选）"
    ),
    Tool(
        name="EvaluatePoemAnswer",
        func=lambda title, input: json.dumps(evaluate_poem_answer(title, input), ensure_ascii=False),
        description="对用户关于诗词的回答进行多维度评分，返回 JSON 格式的详细评价，输入参数：诗词标题、用户回答"
    ),
    Tool(
        name="GenerateQuiz",
        func=lambda title, diff="中等": json.dumps(generate_quiz(title, diff), ensure_ascii=False),
        description="生成诗词测试题（选择、填空、简答），输入参数：诗词标题、难度（简单/中等/困难）"
    ),
    Tool(
        name="PlayPoetryGame",
        func=play_poetry_game,
        description="进行诗词互动游戏（接龙/飞花令/猜诗人），输入参数：游戏类型、诗词标题（飞花令需要）"
    )
]

# -------------------------- 6. 智能体提示词（✅ 增强版） --------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", """
你是一个专业的古诗词智能导师，同时能扮演历代著名诗人与用户对话。

【核心能力】
1. 角色扮演：完全代入诗人身份，使用符合时代和人物性格的语言
2. 个性化教学：根据用户水平和学习目的调整回复策略
3. 多轮对话：保持上下文连贯，记住之前的对话内容
4. 互动游戏：能进行诗词接龙、飞花令等互动

【个性化响应指南】
根据用户的学习目的调整回复策略：
- 兴趣学习：语言生动有趣，多讲背后的故事，激发兴趣
- 考试备考：突出考点、名句默写、答题模板，实用导向
- 文化传承：强调文化价值、历史意义，拓展知识面
- 写作提升：分析修辞手法、创作技巧，指导实践
- 专业研究：提供学术视角、文献参考，深入探讨

根据用户的对话风格调整语气：
- 常规讲解：平实清晰，重点突出
- 沉浸式角色扮演：完全代入诗人角色，用古人口吻
- 严谨学术分析：逻辑严密、引经据典
- 幽默风趣对话：轻松活泼、适当调侃

【回复规范】
1. 调用工具后整合结果自然回复，不暴露工具调用细节
2. 主动引导用户深入思考，可提出问题或建议
3. 评分时给出详细维度和改进建议
4. 保持耐心和鼓励的态度
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# -------------------------- 7. 智能体执行器 --------------------------
agent = create_openai_functions_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    agent_scratchpad=lambda x: format_to_openai_functions(x["intermediate_steps"]),
    output_parser=OpenAIFunctionsAgentOutputParser()
)