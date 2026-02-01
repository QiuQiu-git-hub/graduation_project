import streamlit as st
import pandas as pd
# 数据库相关
from database import init_db, get_or_create_user, save_record, get_user_history
# 知识库和智能体
from knowledge_base import POETRY_DB, agent_executor

# 1. 页面基础配置
st.set_page_config(page_title="AI古诗词情景教学平台", layout="wide")
init_db()  # 启动初始化数据库

# 2. 侧边栏：个性化管理+学习历史
with st.sidebar:
    st.title("🎓 个性化学籍管理")
    username = st.text_input("请输入你的名字/学号", "Student_01")
    # 学习风格与知识库工具参数匹配
    style = st.selectbox(
        "选择学习风格", 
        ["常规讲解", "沉浸式角色扮演", "严谨学术分析", "幽默风趣对话"]
    )
    
    if st.button("登录/更新画像"):
        get_or_create_user(username, style)
        st.success(f"欢迎，{username}！已切换为【{style}】模式。")

    st.divider()
    st.markdown("### 📚 学习历史")
    history = get_user_history(username)
    if history:
        df = pd.DataFrame(
            [(h.poem_title, h.score, h.timestamp) for h in history], 
            columns=["诗名", "得分", "时间"]
        )
        st.dataframe(df, hide_index=True)
        st.line_chart(df.set_index("时间")["得分"])
    else:
        st.info("暂无学习记录，要求打分并完成对话即可生成～")

# 3. 主界面：古诗词核心交互（无记忆，按需打分）
st.title("🏯 AIGC 古诗词情景教学平台")

# 选择古诗
selected_poem = st.selectbox("请选择要学习的古诗", list(POETRY_DB.keys()))
poem_data = POETRY_DB[selected_poem]

# 展示原诗与背景
with st.expander("📖 原诗与创作背景", expanded=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"**《{selected_poem}》**")
        st.markdown(f"*{poem_data['author']}*")
        st.text(poem_data['content'].replace("。", "。\n").replace("，", "，\n"))
    with col2:
        st.info(f"**创作背景**：{poem_data['context']}\n\n**情景设定**：{poem_data['role_setting']}")

st.divider()

# 核心聊天交互（按需打分：用户要求才打分，否则仅回复）
st.subheader(f"🗣️ 与 {poem_data['author']} 隔空对话")
st.caption("提示：输入含「打分/评分/评价/判分」等关键词，即可为你的理解打分～")
# 初始化会话聊天记录（仅用于页面渲染）
if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染历史聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 清空聊天记录按钮
if st.session_state.messages:
    if st.button("🗑️ 清空聊天记录", type="secondary"):
        st.session_state.messages = []
        st.rerun()

# 定义打分关键词库，用户输入含任意一个即判定为需要打分
SCORE_KEYWORDS = ["打分", "评分", "评价", "判分", "评点", "给分", "估分"]
# 接收用户输入
if user_input := st.chat_input("请输入你的问题/感悟...（要求打分请含打分/评分等关键词）"):
    # 1. 渲染并追加用户输入
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. 判断用户是否需要打分（核心：匹配关键词库）
    need_score = any(keyword in user_input for keyword in SCORE_KEYWORDS)
    
    # 3. 动态构造智能体指令（按需拼接评分要求）
    with st.spinner(f"{poem_data['author']} 正在构思回复..."):
        # 基础指令：仅角色对话
        base_instruction = f"""
请以{poem_data['author']}的角色，结合《{selected_poem}》的创作背景，按【{style}】风格自然回复用户问题：{user_input}；
无需额外输出无关内容，回复贴合诗人身份和情景设定。
        """.strip()
        
        # 若需要打分，追加评分指令
        if need_score:
            agent_input = base_instruction + f"""
额外要求：对用户的这段输入做0-100分的国学专业评分，仅在回复末尾添加纯数字分数，无其他评分相关解释。
            """.strip()
        else:
            agent_input = base_instruction  # 不打分，仅基础对话指令
        
        # 调用智能体（无记忆，传空chat_history）
        agent_result = agent_executor.invoke({
            "input": agent_input,
            "chat_history": []
        })
        ai_reply = agent_result["output"]
        score = None  # 初始化评分为空

        # 4. 按需提取评分（仅用户要求时执行）
        if need_score:
            try:
                # 筛选最后一个纯数字作为评分
                score_str = [s for s in ai_reply.split() if s.isdigit()][-1]
                score = int(score_str)
                # 评分范围校验，超出则兜底80分
                score = score if 0 <= score <= 100 else 80
                # 移除回复中的数字评分，保留纯对话内容
                ai_reply = ai_reply.replace(score_str, "").strip().rstrip("，。：、")
            except:
                score = 80  # 解析失败兜底评分
                ai_reply = ai_reply + "（评分解析失败，默认给出80分）"

        # 5. 持久化存储学习记录（有评分则存分数，无则存None/0，适配数据库）
        save_record(username, selected_poem, user_input, ai_reply, score if score else 0)

    # 6. 渲染AI回复（按需展示评分）
    if need_score and score is not None:
        # 有评分：拼接评分展示
        full_reply = f"{ai_reply} \n\n **📝 智能国学评分**：{score}分"
        # 追加带评分的回复到会话
        st.session_state.messages.append({"role": "assistant", "content": full_reply})
        with st.chat_message("assistant"):
            st.markdown(full_reply)
            # 评分互动提示
            if score < 60:
                st.warning("💪 继续加油！尝试结合创作背景体会诗人心境～")
            elif score >= 90:
                st.balloons()
                st.success("🎉 太棒了！对诗词的理解非常到位～")
    else:
        # 无评分：仅展示纯回复
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        with st.chat_message("assistant"):
            st.markdown(ai_reply)