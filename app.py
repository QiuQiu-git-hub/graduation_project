# app.py
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
from database import init_db, register_user, login_user, get_user_info, update_user_profile, save_record, get_user_history
from knowledge_base import POETRY_DB, agent_executor, evaluate_poem_answer, search_poems_by_content, get_poem_by_id, get_all_authors, get_poem_selection_options

st.set_page_config(page_title="AI 古诗词情景教学平台", layout="wide")
init_db()

# 2. 会话状态管理
def init_session_state():
    """初始化会话状态"""
    if "logged_in" not in st.session_state:
        query_params = st.query_params
        saved_username = query_params.get("username")
        saved_logged_in = query_params.get("logged_in")
        
        if saved_username and saved_logged_in == "true":
            st.session_state.logged_in = True
            st.session_state.username = saved_username
            st.session_state.user_profile = get_user_info(saved_username)
        else:
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_profile = {}
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_score_detail" not in st.session_state:
        st.session_state.last_score_detail = None
    if "show_all_history" not in st.session_state:
        st.session_state.show_all_history = False
    if "search_keyword" not in st.session_state:
        st.session_state.search_keyword = ""
    if "selected_author" not in st.session_state:
        st.session_state.selected_author = "全部"

init_session_state()

# 3. 登录/注册页面（未登录时显示）
if not st.session_state.logged_in:
    st.title("🏯 AI 古诗词情景教学平台")
    st.markdown("### 欢迎使用！请先登录或注册")
    
    tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])
    
    with tab1:
        st.markdown("#### 已有账号？请登录")
        login_user_input = st.text_input("用户名/学号", key="login_username")
        login_password = st.text_input("密码", type="password", key="login_password")
        
        if st.button("登录", key="login_btn"):
            if login_user_input and login_password:
                if login_user(login_user_input, login_password):
                    st.session_state.logged_in = True
                    st.session_state.username = login_user_input
                    st.session_state.user_profile = get_user_info(login_user_input)
                    st.query_params["username"] = login_user_input
                    st.query_params["logged_in"] = "true"
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
            else:
                st.warning("请输入用户名和密码")
    
    with tab2:
        st.markdown("#### 新用户？请注册")
        reg_user_input = st.text_input("设置用户名/学号", key="reg_username")
        reg_password = st.text_input("设置密码", type="password", key="reg_password")
        reg_password_confirm = st.text_input("确认密码", type="password", key="reg_password_confirm")
        
        st.markdown("**个性化设置**")
        reg_style = st.selectbox(
            "选择对话风格",
            ["常规讲解", "沉浸式角色扮演", "严谨学术分析", "幽默风趣对话"],
            key="reg_style"
        )
        reg_purpose = st.selectbox(
            "学习古诗词的目的",
            ["兴趣学习", "考试备考"],
            key="reg_purpose"
        )
        
        if st.button("注册", key="reg_btn"):
            if not reg_user_input or not reg_password:
                st.warning("请填写用户名和密码")
            elif reg_password != reg_password_confirm:
                st.error("两次密码输入不一致")
            else:
                if register_user(reg_user_input, reg_password, reg_style, reg_purpose):
                    st.success("注册成功！请登录")
                else:
                    st.error("用户名已存在")

# 4. 主界面（登录后显示）
else:
    # 侧边栏：用户信息 + 学习历史
    with st.sidebar:
        st.title("🎓 个人中心")
        st.markdown(f"**👤 用户**：{st.session_state.username}")
        st.markdown(f"**📖 风格**：{st.session_state.user_profile.get('learning_style', '未设置')}")
        st.markdown(f"**🎯 目的**：{st.session_state.user_profile.get('learning_purpose', '兴趣学习')}")
        
        st.divider()
        
        st.markdown("### ⚙️ 修改学习配置")
        new_style = st.selectbox(
            "对话风格",
            ["常规讲解", "沉浸式角色扮演", "严谨学术分析", "幽默风趣对话"],
            key="sidebar_style"
        )
        new_purpose = st.selectbox(
            "学习目的",
            ["兴趣学习", "考试备考"],
            key="sidebar_purpose"
        )
        
        if st.button("保存配置", key="save_profile"):
            update_user_profile(st.session_state.username, new_style, new_purpose)
            st.session_state.user_profile = get_user_info(st.session_state.username)
            st.success("配置已更新！")
        
        st.divider()
        
        if st.button("🚪 退出登录", key="logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_profile = {}
            st.session_state.messages = []
            st.session_state.last_score_detail = None
            st.session_state.show_all_history = False
            st.query_params["username"] = ""
            st.query_params["logged_in"] = ""
            st.rerun()
        
        # 📚 学习历史
        st.divider()
        st.markdown("### 📚 学习历史")
        
        history = get_user_history(st.session_state.username)
        if history:
            history = sorted(history, key=lambda x: x.timestamp, reverse=True)
            preview_history = history[:3]
            
            for h in preview_history:
                if h.score is None:
                    color = "#6c757d"
                    emoji = "📝"
                    score_text = "未评分"
                elif h.score >= 90:
                    color = "#28a745"
                    emoji = "🏆"
                    score_text = f"{h.score}分"
                elif h.score >= 75:
                    color = "#17a2b8"
                    emoji = "⭐"
                    score_text = f"{h.score}分"
                elif h.score >= 60:
                    color = "#ffc107"
                    emoji = "📖"
                    score_text = f"{h.score}分"
                else:
                    color = "#dc3545"
                    emoji = "💪"
                    score_text = f"{h.score}分"
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 12px;
                    margin: 8px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: #333;">{emoji} {h.poem_title}</span>
                        <span style="
                            background: {color};
                            color: white;
                            padding: 4px 10px;
                            border-radius: 12px;
                            font-size: 12px;
                            font-weight: bold;
                        ">
                            {score_text}
                        </span>
                    </div>
                    <div style="
                        color: #666;
                        font-size: 11px;
                        margin-top: 6px;
                        display: flex;
                        align-items: center;
                    ">
                        <span>🕐 {h.timestamp}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if len(history) > 3:
                if st.button(
                    f"📋 更多记录（共{len(history)}条）",
                    key="show_more_history",
                    use_container_width=True
                ):
                    st.session_state.show_all_history = True
                    st.rerun()
            
            scored_records = [h for h in history if h.score is not None]
            if scored_records:
                avg_score = sum(h.score for h in scored_records) / len(scored_records)
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 12px 0;
                    text-align: center;
                ">
                    <div style="font-size: 24px; font-weight: bold;">{avg_score:.1f}</div>
                    <div style="font-size: 12px; opacity: 0.9;">📊 平均得分</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                color: #666;
            ">
                <div style="font-size: 32px; margin-bottom: 8px;">📭</div>
                <div>暂无学习记录～</div>
            </div>
            """, unsafe_allow_html=True)

    # 📋 全部记录弹窗
    if st.session_state.get("show_all_history", False):
        history = get_user_history(st.session_state.username)
        history = sorted(history, key=lambda x: x.timestamp, reverse=True)
        
        st.markdown("### 📚 全部学习记录")
        
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("❌ 关闭", key="close_history_modal", use_container_width=True):
                st.session_state.show_all_history = False
                st.rerun()
        
        st.divider()
        
        if history:
            for i, h in enumerate(history):
                if h.score is None:
                    color = "#6c757d"
                    emoji = "📝"
                    score_text = "未评分"
                elif h.score >= 90:
                    color = "#28a745"
                    emoji = "🏆"
                    score_text = f"{h.score}分"
                elif h.score >= 75:
                    color = "#17a2b8"
                    emoji = "⭐"
                    score_text = f"{h.score}分"
                elif h.score >= 60:
                    color = "#ffc107"
                    emoji = "📖"
                    score_text = f"{h.score}分"
                else:
                    color = "#dc3545"
                    emoji = "💪"
                    score_text = f"{h.score}分"
                
                col_idx = i % 2
                if col_idx == 0:
                    cols = st.columns(2)
                
                with cols[col_idx]:
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        border-left: 4px solid {color};
                        border-radius: 8px;
                        padding: 12px;
                        margin: 4px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold; color: #333; font-size: 13px;">{emoji} {h.poem_title}</span>
                        </div>
                        <div style="
                            color: #666;
                            font-size: 11px;
                            margin-top: 6px;
                            display: flex;
                            justify-content: space-between;
                        ">
                            <span>🕐 {h.timestamp}</span>
                            <span style="
                                background: {color};
                                color: white;
                                padding: 2px 8px;
                                border-radius: 10px;
                                font-size: 11px;
                                font-weight: bold;
                            ">{score_text}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                if col_idx == 1:
                    st.markdown("")
        else:
            st.info("暂无学习记录～")
        
        st.divider()
        
        if st.button("✅ 完成", key="modal_done", use_container_width=True, type="primary"):
            st.session_state.show_all_history = False
            st.rerun()
        
        st.divider()

    # 主界面
    st.title("🏯 AIGC 古诗词情景教学平台")
    
    # 📌 内容搜索框 + 作者筛选（✅ 核心功能）
    st.markdown("### 🔍 诗词检索")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_keyword = st.text_input(
            "📝 输入诗句或关键词", 
            placeholder="例如：明月几时有、大江东去、春眠不觉晓...",
            key="search_keyword_input",
            value=st.session_state.search_keyword
        )
    with col2:
        all_authors = ["全部"] + get_all_authors()
        selected_author = st.selectbox(
            "📚 作者筛选", 
            all_authors, 
            key="select_author",
            index=all_authors.index(st.session_state.selected_author) if st.session_state.selected_author in all_authors else 0
        )
    
    # 更新会话状态
    if search_keyword != st.session_state.search_keyword:
        st.session_state.search_keyword = search_keyword
    if selected_author != st.session_state.selected_author:
        st.session_state.selected_author = selected_author
    
    # 根据搜索和作者过滤诗词
    poem_options = search_poems_by_content(search_keyword, selected_author)
    
    # 显示搜索结果统计
    if search_keyword:
        st.caption(f"📊 找到 {len(poem_options)} 首匹配的诗词")
    
    # 选择古诗
    if poem_options:
        selected_display = st.selectbox(
            "请选择要学习的古诗词", 
            list(poem_options.keys()), 
            key="select_poem"
        )
        selected_poem_id = poem_options[selected_display]
        poem_data = get_poem_by_id(selected_poem_id)
        
        # 展示原诗与背景
        with st.expander("📖 原诗展示", expanded=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"**《{poem_data['title']}**")
                st.markdown(f"*{poem_data['author']}*")
                st.text(poem_data['content'].replace("。", "。\n").replace("，", "，\n"))
            with col2:
                st.markdown(f"**作者**：{poem_data['author']}")
                st.markdown(f"**字数**：{len(poem_data['content'])}字")
        
        st.divider()
        
        # 核心聊天交互
        st.subheader(f"🗣️ 与 {poem_data['author']} 隔空对话")
        st.caption(f"提示：当前学习目的【{st.session_state.user_profile.get('learning_purpose', '兴趣学习')}】，智能体将据此调整回复风格")
        
        user_level = st.selectbox(
            "当前学习水平",
            ["初级", "中级", "高级"],
            key="user_level"
        )
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if st.session_state.last_score_detail:
            with st.expander("📊 评分详情", expanded=True):
                detail = st.session_state.last_score_detail
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.metric("总分", f"{detail['total_score']}分")
                with col2:
                    st.markdown(f"**💡 评价**：{detail['feedback']}")
                
                cols = st.columns(5)
                for i, (dim, score) in enumerate(detail['dimensions'].items()):
                    cols[i].metric(dim, f"{score}分")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### ✅ 优点")
                    for s in detail.get('strengths', []):
                        st.write(f"- {s}")
                with col2:
                    st.markdown("### 🔧 改进建议")
                    for s in detail.get('suggestions', []):
                        st.write(f"- {s}")
        
        if st.session_state.messages:
            if st.button("🗑️ 清空聊天记录", type="secondary"):
                st.session_state.messages = []
                st.session_state.last_score_detail = None
                st.rerun()
        
        SCORE_KEYWORDS = ["打分", "评分", "评价", "判分", "评点", "给分", "估分"]
        
        if user_input := st.chat_input("请输入你的问题/感悟...（要求打分请含打分/评分等关键词）"):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            
            need_score = any(keyword in user_input for keyword in SCORE_KEYWORDS)
            
            with st.spinner(f"{poem_data['author']} 正在构思回复..."):
                base_instruction = f"""
请以{poem_data['author']}的角色，结合《{poem_data['title']}》的创作背景回复用户。
用户学习风格：【{st.session_state.user_profile.get('learning_style', '常规讲解')}】
用户学习目的：【{st.session_state.user_profile.get('learning_purpose', '兴趣学习')}】
用户水平：【{user_level}】

用户问题：{user_input}
                """.strip()
                
                if need_score:
                    score_detail = evaluate_poem_answer(selected_poem_id, user_input)
                    st.session_state.last_score_detail = score_detail
                    score = score_detail['total_score']
                    ai_reply = f"{score_detail['feedback']}\n\n参考要点：{score_detail.get('reference_answer', '')}"
                else:
                    agent_input = base_instruction
                    agent_result = agent_executor.invoke({
                        "input": agent_input,
                        "chat_history": []
                    })
                    ai_reply = agent_result["output"]
                    score = 0
                
                save_record(
                    st.session_state.username, 
                    poem_data['title'],
                    user_input, 
                    ai_reply, 
                    score if need_score and score > 0 else None
                )
            
            if need_score and score > 0:
                full_reply = f"{ai_reply} \n\n **📝 智能国学评分**：{score}分"
                st.session_state.messages.append({"role": "assistant", "content": full_reply})
                with st.chat_message("assistant"):
                    st.markdown(full_reply)
                    if score < 60:
                        st.warning("💪 继续加油！")
                    elif score >= 90:
                        st.balloons()
                        st.success("🎉 太棒了！")
            else:
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                with st.chat_message("assistant"):
                    st.markdown(ai_reply)
    else:
        st.warning("未找到匹配的诗词，请尝试其他关键词或作者")
        
        # 显示热门搜索建议
        st.markdown("### 💡 热门搜索建议")
        suggestions = ["明月", "春风", "江南", "落花", "相思", "明月几时有", "大江东去"]
        cols = st.columns(4)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 4]:
                if st.button(f"🔍 {suggestion}", key=f"suggest_{suggestion}"):
                    st.session_state.search_keyword = suggestion
                    st.rerun()