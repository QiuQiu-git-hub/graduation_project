# knowledge_base.py
import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

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

# -------------------------- 3. 加载诗词数据库 --------------------------
def load_poetry_db():
    """从 all_poems_perfect.json 加载诗词数据"""
    json_path = os.path.join(os.path.dirname(__file__), "all_poems_perfect.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            poems = json.load(f)
        
        poetry_db = {}
        for i, poem in enumerate(poems):
            title = poem.get("title", "")
            author = poem.get("author", "")
            unique_id = f"{title}##{author}##{i}"
            poetry_db[unique_id] = {
                "id": unique_id,
                "title": title,
                "author": author,
                "content": poem.get("content", ""),
                "complete_lines": poem.get("complete_lines", []),
                "dynasty": poem.get("dynasty", ""),
                "theme": poem.get("theme", "")
            }
        return poetry_db
    except Exception as e:
        print(f"加载诗词数据库失败：{e}")
        return {}

POETRY_DB = load_poetry_db()

# -------------------------- 4. 内容检索功能 --------------------------
def search_poems_by_content(keyword: str, author: str = "全部") -> dict:
    """根据诗词内容/标题搜索诗词"""
    results = {}
    keyword = keyword.strip()
    
    for poem_id, data in POETRY_DB.items():
        if author != "全部" and data['author'] != author:
            continue
        
        if keyword:
            match = (
                keyword in data['title'] or 
                keyword in data['author'] or 
                keyword in data['content']
            )
            if not match:
                continue
        
        display_name = f"{data['title']} - {data['author']}"
        results[display_name] = poem_id
    
    return results

def get_poem_by_id(poem_id: str):
    """根据唯一 ID 获取诗词数据"""
    return POETRY_DB.get(poem_id)

def get_all_authors():
    """获取所有作者列表"""
    return sorted(set(data['author'] for data in POETRY_DB.values()))

# -------------------------- 5. 智能问答功能 --------------------------

def generate_single_poem_question(poem_id: str, asked_questions: list = None) -> dict:
    """
    生成单道关于诗词的智能问答题目，并避免与已问问题重复
    :param poem_id: 诗词ID
    :param asked_questions: 已经问过的问题文本列表 (用于去重)
    :return: 单个问题字典 {"question": "...", "category": "...", "difficulty": "..."}
    """
    poem = get_poem_by_id(poem_id)
    if not poem:
        return {"question": "系统错误：诗词不存在", "category": "未知", "difficulty": "未知"}
    
    # 构建已问问题的提示文本
    history_prompt = ""
    if asked_questions and len(asked_questions) > 0:
        # 只传最近5个作为参考，节省token，同时足以让LLM理解语境
        recent_questions = asked_questions[-5:]
        history_list = "\n".join([f"- {q}" for q in recent_questions])
        history_prompt = f"""
【重要约束 - 防重复】
以下问题是之前已经问过的，请**绝对不要**再生成类似、相同或角度过于接近的问题：
{history_list}
请尝试从其他未被涉及的角度（如不同的修辞、不同的意象、不同的背景细节、字词赏析等）进行出题。
"""
    else:
        history_prompt = "【重要约束】这是第一道题，请选择一个最核心、最经典的切入点进行提问。"

    prompt = f"""
【出题任务】
你是一位国学教授，正在针对特定诗词出考题。
诗词：《{poem['title']}》
作者：{poem['author']}
朝代：{poem.get('dynasty', '未知')}
内容：{poem['content']}

{history_prompt}

请基于上述诗词的具体内容、意象、情感或背景，生成 1 道**独特且具体**的问题。
避免生成泛泛而谈的问题（如“这首诗好在哪里？”），问题必须指向诗词中的具体诗句、特定意象或具体历史背景。

按以下 JSON 格式返回（仅返回 JSON 对象，无其他文字，无 Markdown 标记）：
{{
    "question": "问题内容",
    "category": "背景/意境/修辞/情感/名句/字词/特色",
    "difficulty": "简单/中等/困难"
}}
    """
    
    try:
        response = llm.invoke(prompt)
        # 清理可能的 markdown 代码块标记
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"生成单题失败: {e}")
        # 降级返回默认问题
        return {
            "question": "请结合全诗，谈谈你对这首诗整体意境的理解？", 
            "category": "意境", 
            "difficulty": "中等"
        }

def evaluate_poem_answer(poem_id: str, user_input: str) -> dict:
    """多维度评分"""
    poem = get_poem_by_id(poem_id)
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
诗词：《{poem['title']}》
作者：{poem['author']}
内容：{poem['content']}

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
        "内容理解": 分数,
        "背景关联": 分数,
        "艺术鉴赏": 分数,
        "情感体会": 分数,
        "表达质量": 分数
    }},
    "total_score": 总分,
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

def chat_with_poet(poem_id: str, user_input: str, user_style: str = "常规讲解", user_level: str = "中级") -> str:
    """与诗人角色对话"""
    poem = get_poem_by_id(poem_id)
    if not poem:
        return f"系统暂未收录这首诗词，无法对话。"
    
    level_instruction = {
        "初级": "请用简单易懂的语言，避免过多专业术语，多举例子帮助理解。",
        "中级": "适当使用专业术语，兼顾深度和可读性。",
        "高级": "可以深入探讨学术问题，引用相关文献和研究。"
    }
    
    prompt = f"""
你是一位古代诗人，现在要与用户对话。

【诗词信息】
标题：《{poem['title']}》
作者：{poem['author']}
内容：{poem['content']}

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

# -------------------------- 6. 学习报告生成 --------------------------
def generate_report_content(report_data: dict) -> str:
    """生成学习报告文本内容"""
    content = f"""
=====================================
    🏯 AI 古诗词学习报告
=====================================

📋 基本信息
   用户名：{report_data.get('username', '未知')}
   当前等级：{report_data.get('level', '小学徒')}
   总积分：{report_data.get('total_points', 0)}
   全局排名：第{report_data.get('rank', 0)}名

📊 学习统计
   学习记录总数：{report_data.get('total_records', 0)}条
   平均得分：{report_data.get('avg_score', 0)}分
   已学诗词：{report_data.get('poems_learned', 0)}首
   掌握诗词：{report_data.get('mastered_poems', 0)}首

📅 账户信息
   注册时间：{report_data.get('created_at', '未知')}
   最近登录：{report_data.get('last_login', '未知')}

=====================================
    继续努力，更上一层楼！
=====================================
    """
    return content

# -------------------------- 7. 快捷问题模板 --------------------------
QUICK_QUESTIONS = [
    "这首诗的创作背景是什么？",
    "请帮我分析这首诗的意境",
    "这首诗有哪些修辞手法？",
    "诗人表达了怎样的情感？",
    "请解释诗中名句的含义",
    "这首诗的写作特点是什么？"
]

# -------------------------- 8. 工具封装 --------------------------
tools = [
    Tool(
        name="RetrievePoem",
        func=lambda poem_id: f"""
【诗词档案】
标题：《{get_poem_by_id(poem_id)['title'] if get_poem_by_id(poem_id) else '未知'}》
作者：{get_poem_by_id(poem_id)['author'] if get_poem_by_id(poem_id) else '未知'}
内容：{get_poem_by_id(poem_id)['content'] if get_poem_by_id(poem_id) else '未知'}
        """,
        description="检索古诗词的详细信息"
    ),
    Tool(
        name="ChatWithPoet",
        func=lambda args: chat_with_poet(args[0], args[1], args[2] if len(args) > 2 else "常规讲解"),
        description="以诗词作者的角色与用户对话"
    ),
    Tool(
        name="EvaluatePoemAnswer",
        func=lambda args: json.dumps(evaluate_poem_answer(args[0], args[1]), ensure_ascii=False),
        description="对用户关于诗词的回答进行多维度评分"
    ),
    Tool(
        name="GenerateQuestions",
        func=lambda poem_id: json.dumps(generate_single_poem_question(poem_id), ensure_ascii=False),
        description="生成关于诗词的智能问答题目"
    )
]

# -------------------------- 9. 智能体提示词 --------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", """
你是一个专业的古诗词智能导师，同时能扮演历代著名诗人与用户对话。

【核心能力】
1. 角色扮演：完全代入诗人身份，使用符合时代和人物性格的语言
2. 个性化教学：根据用户水平和学习目的调整回复策略
3. 多轮对话：保持上下文连贯，记住之前的对话内容
4. 互动问答：能生成问题并评分

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

# -------------------------- 10. 智能体执行器 --------------------------
agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    return_intermediate_steps=False
)