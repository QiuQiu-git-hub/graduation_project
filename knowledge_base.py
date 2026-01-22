#RAG知识库
# knowledge_base.py
import json
from openai import OpenAI

# --- 配置你的大模型 API ---
# 这里以 DeepSeek 为例，你也可以换成 OpenAI 或其他兼容接口
API_KEY = "sk-97b996cc43c640a09b4a3ef40366bcc8"  # 【请在此处填入你的 API Key】
BASE_URL = "https://api.deepseek.com"      # 【请在此处填入对应的 Base URL】

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 1. 模拟本地古诗词知识库 (RAG 的数据源)
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
        "context": "这首诗写于孟浩然隐居鹿门山时。描写了春日早晨的景色，表达了诗人对春天的喜爱和怜惜。",
        "role_setting": "你是孟浩然，一位隐居山林的雅士。你刚睡醒，推开窗户看到满地落花，语气慵懒、闲适且温和。"
    }
}

# 2. AIGC 情景生成功能
def chat_with_poet(poem_title, user_input, user_style):
    data = POETRY_DB.get(poem_title)
    if not data:
        return "系统暂未收录此诗。", 0

    # 构建 Prompt (提示词工程)
    system_prompt = f"""
    {data['role_setting']}
    
    你需要结合这首诗的背景：{data['context']}
    用户的学习偏好是：{user_style}。
    
    请用你扮演的角色（{data['author']}）与用户对话。
    如果用户是在回答你的问题或解释诗句，请进行点评。
    """

    response = client.chat.completions.create(
        model="deepseek-chat", # 请根据你的服务商修改模型名称，如 gpt-3.5-turbo
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content

# 3. 智能评估功能
def evaluate_student(poem_title, user_input):
    """专门用于给用户的回答打分"""
    data = POETRY_DB.get(poem_title)
    
    prompt = f"""
    诗词：《{poem_title}》
    内容：{data['content']}
    用户的发言："{user_input}"
    
    请作为一个严谨的国学老师，给这句发言打分（0-100分）。
    只返回一个纯数字，不要任何文字解释。
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        score = int(response.choices[0].message.content.strip())
        return score
    except:
        return 80 # 容错处理
