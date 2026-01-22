# app.py
import streamlit as st
import pandas as pd
from database import init_db, get_or_create_user, save_record, get_user_history
from knowledge_base import POETRY_DB, chat_with_poet, evaluate_student

# 1. 页面配置
st.set_page_config(page_title="AI古诗词情景教学平台", layout="wide")
init_db()  # 启动时初始化数据库

# 2. 侧边栏：个性化管理
with st.sidebar:
    st.title("🎓 个性化学籍管理")
    username = st.text_input("请输入你的名字/学号", "Student_01")
    style = st.selectbox("选择学习风格", ["沉浸式角色扮演", "严谨学术分析", "幽默风趣对话"])
    
    if st.button("登录/更新画像"):
        user = get_or_create_user(username, style)
        st.success(f"欢迎，{username}！已为你切换为【{style}】模式。")

    st.divider()
    st.markdown("### 📚 学习历史")
    history = get_user_history(username)
    if history:
        # 简单的数据可视化
        df = pd.DataFrame([(h.poem_title, h.score, h.timestamp) for h in history], 
                          columns=["诗名", "得分", "时间"])
        st.dataframe(df, hide_index=True)
        st.line_chart(df.set_index("时间")["得分"])
    else:
        st.info("暂无学习记录")

# 3. 主界面：情景教学
st.title("🏯 AIGC 古诗词情景教学")

# 选择课程
selected_poem = st.selectbox("请选择要学习的古诗", list(POETRY_DB.keys()))
poem_data = POETRY_DB[selected_poem]

# 展示知识库内容
with st.expander("📖 查看原诗与背景 (知识库)", expanded=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"**《{selected_poem}》**")
        st.markdown(f"*{poem_data['author']}*")
        st.text(poem_data['content'].replace("。", "。\n"))
    with col2:
        st.info(f"**背景知识**：{poem_data['context']}")

st.divider()

# 交互区域
st.subheader(f"🗣️ 与 {poem_data['author']} 对话")
st.caption(f"当前情景：{poem_data['role_setting']}")

# 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史聊天
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入
if user_input := st.chat_input("请输入你的感悟，或向诗人提问..."):
    # 1. 显示用户输入
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. AI 处理 (RAG + AIGC)
    with st.spinner(f"{poem_data['author']} 正在思考..."):
        # 生成回复
        ai_reply = chat_with_poet(selected_poem, user_input, style)
        # 智能评分
        score = evaluate_student(selected_poem, user_input)
        
        # 存入数据库 (持久化存储)
        save_record(username, selected_poem, user_input, ai_reply, score)

    # 3. 显示 AI 回复
    full_reply = f"{ai_reply} \n\n *(智能评估得分: {score})*"
    st.session_state.messages.append({"role": "assistant", "content": full_reply})
    with st.chat_message("assistant"):
        st.markdown(full_reply)
        if score < 60:
            st.warning("继续加油，尝试理解诗人的心境！")
        elif score > 90:
            st.balloons()