import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import AgentExecutor
from langchain.agents.openai_functions_agent.base import create_openai_functions_agent
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage

# -------------------------- 1. 基础配置（无修改） --------------------------
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY") or "sk-97b996cc43c640a09b4a3ef40366bcc8"
BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

# -------------------------- 2. 提前初始化LLM（无修改） --------------------------
llm = ChatOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    model_name=MODEL_NAME,
    temperature=0.7,
    max_tokens=1024
)

# -------------------------- 古诗词知识库（无修改） --------------------------
POETRY_DB = {
    "静夜思": {
        "author": "李白",
        "content": "床前明月光，疑是地上霜。举头望明月，低头思故乡。",
        "context": "写于李白客居扬州时期。在一个月明星稀的夜晚，诗人抬望天空一轮皓月，思乡之情油然而生。",
        "role_setting": "你是李白，正独自一人在扬州的旅舍中，手里拿着一杯酒，看着月亮，语气豪放但带着一丝孤独。"
    },
    "春晓": {
        "author": "孟浩然",
        "content": "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。",
        "context": "写于孟浩然隐居鹿门山时。描写了春日早晨的景色，表达了诗人对春天的喜爱和怜惜。",
        "role_setting": "你是孟浩然，一位隐居山林的雅士。你刚睡醒，推开窗户看到满地落花，语气慵懒、闲适且温和。"
    }
}

# -------------------------- 3. 工具函数（无修改） --------------------------
def retrieve_poem(poem_title: str) -> str:
    poem = POETRY_DB.get(poem_title)
    if not poem:
        return f"系统暂未收录《{poem_title}》这首诗词，无法提供相关服务。"
    return f"""
诗词：《{poem_title}》
作者：{poem['author']}
内容：{poem['content']}
创作背景：{poem['context']}
角色设定：{poem['role_setting']}
    """.strip()

def chat_with_poet(poem_title: str, user_input: str, user_style: str = "常规讲解") -> str:
    poem = POETRY_DB.get(poem_title)
    if not poem:
        return f"系统暂未收录《{poem_title}》这首诗词，无法对话。"
    prompt = f"""
    {poem['role_setting']}
    你需要结合这首诗的背景：{poem['context']}
    用户的学习偏好是：{user_style}。
    请用你扮演的角色（{poem['author']}）与用户对话，若用户解释诗句则进行点评。
    用户输入：{user_input}
    """
    response = llm.invoke(prompt)
    return response.content

def evaluate_poem_answer(poem_title: str, user_input: str) -> int:
    poem = POETRY_DB.get(poem_title)
    if not poem:
        return 0
    prompt = f"""
    诗词：《{poem_title}》
    内容：{poem['content']}
    用户的发言："{user_input}"
    请作为一个严谨的国学老师，给这句发言打分（0-100分）。
    只返回一个纯数字，不要任何文字解释。
    """
    try:
        response = llm.invoke(prompt)
        score = int(response.content.strip())
        return score if 0 <= score <= 100 else 80
    except:
        return 80

# -------------------------- 4. 工具封装（无修改） --------------------------
tools = [
    Tool(
        name="RetrievePoem",
        func=retrieve_poem,
        description="""当需要检索古诗词的详细信息（作者、内容、创作背景、角色设定）时使用，
        输入参数是诗词的标题（如：静夜思、春晓）"""
    ),
    Tool(
        name="ChatWithPoet",
        func=chat_with_poet,
        description="""当需要以诗词作者的角色与用户对话、解释诗句、点评用户理解时使用，
        输入参数依次是：诗词标题、用户输入、用户学习偏好（可选，默认常规讲解）"""
    ),
    Tool(
        name="EvaluatePoemAnswer",
        func=evaluate_poem_answer,
        description="""当需要对用户关于诗词的回答/理解进行打分时使用，仅返回0-100的纯数字，
        输入参数依次是：诗词标题、用户的回答内容"""
    )
]

# -------------------------- 5. 智能体提示词（✅ 核心修改2：简化模板，适配新智能体） --------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", """
你是一个专业的古诗词智能导师，擅长根据用户需求选择合适工具完成任务。
严格按工具参数要求调用，工具执行后整合结果自然回复，无需暴露工具调用细节。
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    # 仅保留核心占位符，移除多余说明，适配OpenAI函数智能体
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# -------------------------- 6. 智能体执行器（✅ 核心修改3：创建OpenAI函数智能体，根治bug） --------------------------
# 初始化OpenAI函数智能体（无隐性参数bug，稳定）
agent = create_openai_functions_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

# 包装为执行器，指定格式化器和解析器（解决agent_scratchpad类型问题）
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    # ✅ 关键：指定格式化器，让agent_scratchpad自动为标准消息列表
    agent_scratchpad=lambda x: format_to_openai_functions(x["intermediate_steps"]),
    output_parser=OpenAIFunctionsAgentOutputParser()
)