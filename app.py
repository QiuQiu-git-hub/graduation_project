# app.py
import streamlit as st
import pandas as pd
from database import (
    init_db, register_user, login_user, get_user_info, update_user_profile,
    save_record, get_user_history, get_mastery, get_leaderboard, get_user_rank,
    generate_learning_report, add_user_points, get_user_achievements, add_achievement
)
from knowledge_base import (
    POETRY_DB, agent_executor, evaluate_poem_answer, search_poems_by_content,
    get_poem_by_id, get_all_authors, QUICK_QUESTIONS, generate_report_content,
    chat_with_poet, generate_single_poem_question
)
import json
from datetime import datetime

st.set_page_config(page_title="AI 古诗词情景教学平台", 
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    })
init_db()

# ==================== 会话状态管理 ====================
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
    
    # 聊天模式消息
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # 测验模式状态
    if "quiz_mode_active" not in st.session_state:
        st.session_state.quiz_mode_active = False
    if "current_quiz_question" not in st.session_state:
        st.session_state.current_quiz_question = None
    if "asked_questions_history" not in st.session_state:
        st.session_state.asked_questions_history = [] # 存储已问过的题目文本，用于去重
    if "last_quiz_score_detail" not in st.session_state:
        st.session_state.last_quiz_score_detail = None
    if "quiz_step" not in st.session_state:
        st.session_state.quiz_step = "question" # 'question' (答题中) 或 'result' (看结果)

    # 其他通用状态
    if "show_all_history" not in st.session_state:
        st.session_state.show_all_history = False
    
    # 【修改点 1】设置默认搜索关键词为 "春晓"
    if "search_keyword" not in st.session_state:
        st.session_state.search_keyword = "春晓"
    if "persist_search_keyword" not in st.session_state:
        st.session_state.persist_search_keyword = "春晓"

    # 【修改点 2】设置默认作者为 "孟浩然" (如果存在该作者，否则保持全部)
    # 注意：这里先设为 "孟浩然"，后续在页面渲染时会校验是否存在
    if "selected_author" not in st.session_state:
        st.session_state.selected_author = "孟浩然"
    if "persist_selected_author" not in st.session_state:
        st.session_state.persist_selected_author = "孟浩然"

    if "current_page" not in st.session_state:
        st.session_state.current_page = "learning"
    
    # 保存选中的诗词 ID 和显示名称（用于刷新后恢复）
    # 【修改点 3】尝试预加载《春晓》的 ID
    if "selected_poem_id" not in st.session_state:
        # 尝试获取春晓的ID，如果找不到则保持 None，页面会正常显示搜索结果列表
        try:
            # 先临时搜索一下
            default_poems = search_poems_by_content("春晓", "孟浩然")
            if default_poems:
                # 假设第一首就是春晓，或者遍历查找标题为春晓的
                spring_dawn_id = None
                spring_dawn_display = None
                for display_name, pid in default_poems.items():
                    if "春晓" in display_name:
                        spring_dawn_id = pid
                        spring_dawn_display = display_name
                        break
                
                # 如果没找到精确匹配，取第一个结果（通常搜索春晓第一个就是）
                if not spring_dawn_id and default_poems:
                    first_key = list(default_poems.keys())[0]
                    spring_dawn_id = default_poems[first_key]
                    spring_dawn_display = first_key

                st.session_state.selected_poem_id = spring_dawn_id
                st.session_state.selected_poem_display = spring_dawn_display
            else:
                st.session_state.selected_poem_id = None
                st.session_state.selected_poem_display = None
        except Exception:
            # 防止数据库未初始化或其他错误导致启动失败
            st.session_state.selected_poem_id = None
            st.session_state.selected_poem_display = None

    if "selected_poem_display" not in st.session_state:
        # 如果上面因为异常没设置，这里兜底
        if st.session_state.selected_poem_id is None:
             st.session_state.selected_poem_display = None

init_session_state()

# ==================== 快捷问题模板 ====================
def show_quick_questions():
    """显示快捷问题模板"""
    st.markdown("### 💬 快捷问题")
    learning_questions = [
        "这首诗的创作背景是什么？",
        "作者想表达什么情感？",
        "诗中有哪些修辞手法？",
        "这首诗的意境如何？",
        "能解释一下这句诗的意思吗？",
        "作者的生平经历是怎样的？",
        "这首诗有什么典故？",
        "类似主题的诗词还有哪些？"
    ]
    cols = st.columns(4)
    for i, question in enumerate(learning_questions[:8]):
        with cols[i % 4]:
            if st.button(f"💭 {question[:10]}...", key=f"quick_{i}", use_container_width=True):
                return question
    return None

# ==================== 掌握程度显示组件 ====================
def show_mastery_badge(mastery_data: dict):
    """显示掌握程度徽章"""
    level = mastery_data.get("mastery_level", "未学习")
    colors = {
        "精通": "#28a745",
        "熟练": "#17a2b8",
        "掌握": "#ffc107",
        "学习中": "#fd7e14",
        "未学习": "#6c757d"
    }
    emojis = {
        "精通": "🏆",
        "熟练": "⭐",
        "掌握": "📖",
        "学习中": "🌱",
        "未学习": "⭕"
    }
    
    color = colors.get(level, "#6c757d")
    emoji = emojis.get(level, "⭕")
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}22 0%, {color}44 100%);
        border: 2px solid {color};
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin: 10px 0;
    ">
        <div style="font-size: 32px; margin-bottom: 5px;">{emoji}</div>
        <div style="font-size: 18px; font-weight: bold; color: {color};">{level}</div>
        <div style="font-size: 12px; color: #666; margin-top: 5px;">
            回答{mastery_data.get('answer_count', 0)}次 | 平均分{mastery_data.get('avg_score', 0):.1f}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== 学习页面 ====================

def show_learning_page():
    """显示学习主页面"""
    
    # 【优化】添加右上角淡雅山水背景图案
    # 使用内联 SVG 确保显示，调整了透明度和位置
    shanshui_css = """
    <style>
    /* 创建一个固定在最上层的容器，但指针事件穿透 */
    .shanshui-container {
        position: fixed;
        top: 0;
        right: 0;
        width: 100%;
        height: 100%;
        pointer-events: none; /* 关键：让鼠标点击穿透到下层按钮 */
        z-index: 9999; /* 确保在最上层，但因为是透明的所以不影响视觉 */
        overflow: hidden;
    }

    /* 山水图案本身 */
    .shanshui-svg {
        position: absolute;
        top: -50px;       /* 向上微调 */
        right: -50px;     /* 向右微调 */
        width: 400px;     /* 图案大小 */
        height: auto;
        opacity: 0.08;    /* 非常淡，不喧宾夺主 */
    }
    </style>
    
    <div class="shanshui-container">
        <!-- 极简水墨山峦 SVG -->
        <svg class="shanshui-svg" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="inkGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:#555555;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#555555;stop-opacity:0.2" />
                </linearGradient>
            </defs>
            <!-- 远山 -->
            <path d="M100,300 Q200,100 300,300 T500,300 T700,300 L800,400 L0,400 Z" fill="url(#inkGradient)" />
            <!-- 近山 -->
            <path d="M50,350 Q150,200 250,350 T450,350 T650,350 L800,400 L0,400 Z" fill="#333333" fill-opacity="0.1" />
        </svg>
    </div>
    """
    st.markdown(shanshui_css, unsafe_allow_html=True)

    st.title("🏯 意通")
    
    
    # --- 以下是原有的业务逻辑，请确保这部分代码完整存在 ---
    
    # 从持久化状态恢复搜索条件
    if st.session_state.persist_search_keyword:
        st.session_state.search_keyword = st.session_state.persist_search_keyword
    if st.session_state.persist_selected_author:
        st.session_state.selected_author = st.session_state.persist_selected_author
    
    # 诗词检索
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
    
    # ... (后续所有原有代码保持不变) ...
    
    # 更新会话状态和持久化状态
    if search_keyword != st.session_state.search_keyword:
        st.session_state.search_keyword = search_keyword
        st.session_state.persist_search_keyword = search_keyword
        # 搜索词改变时清空选中的诗词
        st.session_state.selected_poem_id = None
        st.session_state.selected_poem_display = None
    if selected_author != st.session_state.selected_author:
        st.session_state.selected_author = selected_author
        st.session_state.persist_selected_author = selected_author
        # 作者改变时清空选中的诗词
        st.session_state.selected_poem_id = None
        st.session_state.selected_poem_display = None
    
    # 搜索诗词
    poem_options = search_poems_by_content(search_keyword, selected_author)
    
    if search_keyword:
        st.caption(f"📊 找到 {len(poem_options)} 首匹配的诗词")
    
    # 选择古诗（优先使用会话中保存的选中项）
    if poem_options:
        # 如果有保存的选中诗词，优先使用
        default_index = 0
        if st.session_state.selected_poem_display and st.session_state.selected_poem_display in poem_options:
            default_index = list(poem_options.keys()).index(st.session_state.selected_poem_display)
        
        selected_display = st.selectbox(
            "请选择要学习的古诗词", 
            list(poem_options.keys()), 
            key="select_poem",
            index=default_index
        )
        
        # 【关键修改】检测是否切换了诗词
        new_poem_id = poem_options[selected_display]
        old_poem_id = st.session_state.selected_poem_id
        
        # 如果 ID 发生变化，说明用户选了新的诗，必须重置测验状态
        if new_poem_id != old_poem_id:
            st.session_state.selected_poem_id = new_poem_id
            st.session_state.selected_poem_display = selected_display
            
            # 重置测验相关状态，确保下一题是新诗的题
            st.session_state.current_quiz_question = None
            st.session_state.asked_questions_history = []
            st.session_state.quiz_step = "question"
            st.session_state.last_quiz_score_detail = None
            
            # 强制刷新页面以应用重置
            st.rerun()
        else:
            # 如果没有切换，保持原有状态
            st.session_state.selected_poem_id = new_poem_id
            st.session_state.selected_poem_display = selected_display
        
        selected_poem_id = st.session_state.selected_poem_id
        poem_data = get_poem_by_id(selected_poem_id)
        
        # 获取掌握程度
        mastery_data = get_mastery(st.session_state.username, selected_poem_id)
        
        # 展示原诗与背景（含掌握程度）
        with st.expander("📖 原诗展示", expanded=True):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.markdown(f"**《{poem_data['title']}**")
                st.markdown(f"*{poem_data['author']}*")
                st.text(poem_data['content'].replace("。", "。\n").replace("，", "，\n"))
            with col2:
                st.markdown(f"**作者**：{poem_data['author']}")
                st.markdown(f"**字数**：{len(poem_data['content'])}字")
                if poem_data.get('dynasty'):
                    st.markdown(f"**朝代**：{poem_data['dynasty']}")
            with col3:
                show_mastery_badge(mastery_data)
        
        st.divider()
        
        # 模式切换 Tab
        tab_chat, tab_quiz = st.tabs(["💬 自由对话", "📝 智能测验"])
        
        # === 标签页 1: 自由对话 ===
        with tab_chat:
            st.subheader(f"🗣️ 与 {poem_data['author']} 隔空对话")
            st.caption("在此模式下，您可以随意提问，诗人将为您解答，不会进行打分。")
            
            user_level = st.selectbox("当前学习水平", ["初级", "中级", "高级"], key="chat_level")
            
            # 显示历史消息
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # 快捷问题
            quick_question = show_quick_questions()
            
            # 处理输入
            user_input = None
            if quick_question:
                user_input = quick_question
            elif prompt := st.chat_input("请输入你的问题...", key="chat_input"):
                user_input = prompt
                
            if user_input:
                st.session_state.chat_messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
                
                with st.spinner("AI 正在回复..."):
                    reply = chat_with_poet(
                        poem_id=selected_poem_id,
                        user_input=user_input,
                        user_style=st.session_state.user_profile.get('learning_style', '常规讲解'),
                        user_level=user_level
                    )
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                with st.chat_message("assistant"):
                    st.markdown(reply)
                    
                # 保存记录 (无分)
                save_record(st.session_state.username, poem_data['title'], selected_poem_id, user_input, reply, score=None)
                
                if quick_question:
                    st.rerun()

        # === 标签页 2: 智能测验 ===
        with tab_quiz:
            st.subheader(f"📝 《{poem_data['title']}》 无限智能测验")
            st.caption("系统每次生成一道新题，确保不重复。答完即可查看评分并进入下一题。")
            
            # 初始化测验：如果还没开始，生成第一题
            if not st.session_state.current_quiz_question:
                with st.spinner("正在生成第一道考题..."):
                    new_q = generate_single_poem_question(selected_poem_id, st.session_state.asked_questions_history)
                    st.session_state.current_quiz_question = new_q
                    st.session_state.quiz_step = "question"
                    st.session_state.last_quiz_score_detail = None

            current_q = st.session_state.current_quiz_question
            
            # 显示当前题目
            st.info(f"**[{current_q.get('category', '综合')}] [{current_q.get('difficulty', '中等')}]**\n\n❓ **{current_q['question']}**")
            
            # 根据步骤显示不同内容
            if st.session_state.quiz_step == "question":
                # --- 答题阶段 ---
                user_answer = st.text_area("请输入您的回答：", key="quiz_answer_input", height=150)
                
                col_submit, _ = st.columns([1, 3])
                if col_submit.button("✅ 提交答案", type="primary", use_container_width=True):
                    if not user_answer.strip():
                        st.warning("请输入回答内容")
                    else:
                        with st.spinner("AI 专家正在评卷..."):
                            # 1. 评分
                            score_detail = evaluate_poem_answer(selected_poem_id, user_answer)
                            st.session_state.last_quiz_score_detail = score_detail
                            
                            # 2. 积分与成就
                            score = score_detail['total_score']
                            points_earned = score // 10
                            if points_earned > 0:
                                add_user_points(st.session_state.username, points_earned)
                                st.session_state.user_profile = get_user_info(st.session_state.username)
                            if score >= 90:
                                add_achievement(st.session_state.username, "high_score", "🏆 高分达人")
                            
                            # 3. 保存记录
                            save_record(
                                st.session_state.username, 
                                poem_data['title'],
                                selected_poem_id,
                                f"[测验] {current_q['question']}", 
                                user_answer, 
                                score
                            )
                            
                            # 4. 切换状态到结果页
                            st.session_state.quiz_step = "result"
                            st.rerun()

            elif st.session_state.quiz_step == "result":
                # --- 结果展示阶段 ---
                detail = st.session_state.last_quiz_score_detail
                
                # 显示评分详情
                st.success(f"🎉 本题得分：**{detail['total_score']} 分**")
                
                with st.expander("📊 查看详细评价", expanded=True):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("总分", f"{detail['total_score']}分")
                    with col2:
                        st.markdown(f"**💡 专家点评**：{detail['feedback']}")
                    
                    cols = st.columns(5)
                    dims = detail.get('dimensions', {})
                    for i, dim in enumerate(["内容理解", "背景关联", "艺术鉴赏", "情感体会", "表达质量"]):
                        cols[i].metric(dim, f"{dims.get(dim, 0)}分")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### ✅ 优点")
                        for s in detail.get('strengths', []):
                            st.write(f"- {s}")
                    with c2:
                        st.markdown("### 🔧 改进建议")
                        for s in detail.get('suggestions', []):
                            st.write(f"- {s}")
                    
                    st.markdown(f"**📖 参考要点**：{detail.get('reference_answer', '')}")

                st.divider()
                
                # 下一题按钮
                if st.button("➡️ 生成下一道新题", type="primary", use_container_width=True):
                    # 1. 将当前问题加入历史
                    st.session_state.asked_questions_history.append(current_q['question'])
                    
                    # 2. 生成新题 (传入历史以去重)
                    with st.spinner("正在构思新题目..."):
                        next_q = generate_single_poem_question(selected_poem_id, st.session_state.asked_questions_history)
                        
                    # 3. 更新状态
                    st.session_state.current_quiz_question = next_q
                    st.session_state.quiz_step = "question"
                    st.session_state.last_quiz_score_detail = None # 清空上一题详情，避免混淆
                    st.rerun()
                    
            # 重置测验按钮
            if st.button("🔄 重置测验记录", type="secondary"):
                st.session_state.current_quiz_question = None
                st.session_state.asked_questions_history = []
                st.session_state.quiz_step = "question"
                st.session_state.last_quiz_score_detail = None
                st.rerun()

    else:
        st.warning("未找到匹配的诗词，请尝试其他关键词或作者")

# ==================== 排行榜页面 ====================
def show_leaderboard_page():
    """显示排行榜页面"""
    st.title("🏆 学习排行榜")
    
    scope = st.radio("排行榜范围", ["全部用户", "同校用户"], horizontal=True)
    scope_map = {"全部用户": "all", "同校用户": "school"}
    
    # 传入当前用户名用于同校筛选
    leaderboard = get_leaderboard(
        limit=20, 
        scope=scope_map[scope],
        current_username=st.session_state.username
    )
    
    if leaderboard:
        # 显示前 3 名
        st.markdown("### 🥇 前三名")
        cols = st.columns(3)
        medals = ["🥇", "🥈", "🥉"]
        for i, user in enumerate(leaderboard[:3]):
            with cols[i]:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #ffd70022 0%, #ffd70044 100%);
                    border: 2px solid #ffd700;
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                ">
                    <div style="font-size: 48px;">{medals[i]}</div>
                    <div style="font-size: 18px; font-weight: bold;">{user['username']}</div>
                    <div style="font-size: 14px; color: #666;">{user.get('grade', '')} | {user['level']}</div>
                    <div style="font-size: 24px; color: #ffd700; font-weight: bold; margin-top: 10px;">
                        {user['total_points']}分
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### 📋 完整排名")
        
        df = pd.DataFrame(leaderboard)
        st.dataframe(
            df[['rank', 'username', 'grade', 'total_points', 'level', 'school']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "rank": "排名",
                "username": "用户名",
                "grade": "年级",
                "total_points": "积分",
                "level": "等级",
                "school": "学校"
            }
        )
        
        # 显示当前用户排名（根据筛选范围）
        if st.session_state.username:
            user_rank = get_user_rank(st.session_state.username, scope_map[scope])
            rank_text = "同校排名" if scope_map[scope] == "school" else "全局排名"
            st.info(f"📍 你的{rank_text}：第 {user_rank} 名")

# ==================== 学习报告页面 ====================
def show_report_page():
    """显示学习报告页面"""
    st.title("📄 学习报告")
    
    if st.button("🔄 生成最新报告", type="primary"):
        st.session_state.report_data = generate_learning_report(st.session_state.username)
        st.rerun()
    
    if hasattr(st.session_state, 'report_data') and st.session_state.report_data:
        report = st.session_state.report_data
        
        # 报告展示
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📊 学习统计")
            
            metrics = st.columns(4)
            metrics[0].metric("📝 学习记录", f"{report.get('total_records', 0)}条")
            metrics[1].metric("📈 平均得分", f"{report.get('avg_score', 0)}分")
            metrics[2].metric("📚 已学诗词", f"{report.get('poems_learned', 0)}首")
            metrics[3].metric("🏆 掌握诗词", f"{report.get('mastered_poems', 0)}首")
        
        with col2:
            st.markdown("### 👤 用户信息")
            st.markdown(f"**用户名**：{report.get('username', '未知')}")
            st.markdown(f"**年级**：{report.get('grade', '未设置')}")
            st.markdown(f"**学校**：{report.get('school', '未设置') or '未填写'}")
            st.markdown(f"**等级**：{report.get('level', '小学徒')}")
            st.markdown(f"**总积分**：{report.get('total_points', 0)}")
            st.markdown(f"**排名**：第{report.get('rank', 0)}名")
        
        st.divider()
        
        # 导出报告
        st.markdown("### 💾 导出报告")
        
        report_content = generate_report_content(report)
        
        st.download_button(
            label="📥 下载文本报告",
            data=report_content,
            file_name=f"学习报告_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
        
        # 成就展示
        st.divider()
        st.markdown("### 🏅 我的成就")
        achievements = get_user_achievements(st.session_state.username)
        if achievements:
            cols = st.columns(3)
            for i, ach in enumerate(achievements):
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="
                        background: #fff3cd;
                        border: 1px solid #ffc107;
                        border-radius: 8px;
                        padding: 15px;
                        text-align: center;
                    ">
                        <div style="font-size: 24px;">🏅</div>
                        <div style="font-weight: bold;">{ach['name']}</div>
                        <div style="font-size: 12px; color: #666;">{ach['earned_at']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("暂无成就，继续学习解锁更多成就！")
    else:
        st.info("点击上方按钮生成学习报告")

# ==================== 侧边栏 ====================
def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.title("🎓 个人中心")
        # 每次显示侧边栏时刷新用户信息（解决积分不更新问题）
        st.session_state.user_profile = get_user_info(st.session_state.username)
        
        st.markdown(f"**👤 用户**：{st.session_state.username}")
        st.markdown(f"**📚 年级**：{st.session_state.user_profile.get('grade', '未设置')}")
        st.markdown(f"**🏫 学校**：{st.session_state.user_profile.get('school', '未填写') or '未填写'}")
        st.markdown(f"**📖 风格**：{st.session_state.user_profile.get('learning_style', '未设置')}")
        st.markdown(f"**🎯 目的**：{st.session_state.user_profile.get('learning_purpose', '兴趣学习')}")
        st.markdown(f"**🏆 等级**：{st.session_state.user_profile.get('level', '小学徒')}")
        st.markdown(f"**⭐ 积分**：{st.session_state.user_profile.get('total_points', 0)}")
        st.divider()
        
        # 导航菜单
        st.markdown("### 🧭 导航")
        
        page_options = {
            "📚 学习": "learning",
            "🏆 排行榜": "leaderboard",
            "📄 学习报告": "report"
        }
        
        for label, page in page_options.items():
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.session_state.current_page = page
                st.rerun()
        
        st.divider()
        
        # 学习配置
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
        
        # 退出登录
        if st.button("🚪 退出登录", key="logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_profile = {}
            st.session_state.chat_messages = []
            st.session_state.current_quiz_question = None
            st.session_state.asked_questions_history = []
            st.session_state.last_quiz_score_detail = None
            st.session_state.persist_search_keyword = ""
            st.session_state.persist_selected_author = "全部"
            st.query_params["username"] = ""
            st.query_params["logged_in"] = ""
            st.rerun()

# ==================== 登录/注册页面 ====================
def show_login_page():
    """显示登录/注册页面"""
    st.title("🏯 意通")
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
        
        # 年级选择（包含大学和其他选项）
        st.markdown("**个人信息**")
        reg_grade = st.selectbox(
            "年级", 
            ["小学", "初中", "高中", "大学", "其他"],
            key="reg_grade"
        )
        reg_school = st.text_input("学校（可选）", key="reg_school")
        
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
            elif len(reg_password) < 6:
                st.error("密码长度至少 6 位")
            else:
                # 调用 register_user，传入 grade 参数
                if register_user(reg_user_input, reg_password, reg_style, reg_purpose, reg_school, reg_grade):
                    st.success("注册成功！请登录")
                else:
                    st.error("用户名已存在")

# ==================== 主程序 ====================
if __name__ == "__main__":
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_sidebar()
        
        # 根据当前页面显示内容
        if st.session_state.current_page == "learning":
            show_learning_page()
        elif st.session_state.current_page == "leaderboard":
            show_leaderboard_page()
        elif st.session_state.current_page == "report":
            show_report_page()