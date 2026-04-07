# database.py
import sqlite3
from datetime import datetime
import hashlib

# ==================== 数据库连接 ====================
DB_PATH = "poetry_platform.db"

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 支持字典式访问
    return conn

# ==================== 数据库初始化 ====================
def init_db():
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            learning_style TEXT DEFAULT '常规讲解',
            learning_purpose TEXT DEFAULT '兴趣学习',
            school TEXT,
            grade TEXT,
            level TEXT DEFAULT '小学徒',
            total_points INTEGER DEFAULT 0,
            created_at TEXT,
            last_login TEXT
        )
    """)
    
    # 学习记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            poem_id TEXT NOT NULL,
            poem_title TEXT NOT NULL,
            user_input TEXT,
            ai_reply TEXT,
            score INTEGER,
            created_at TEXT
        )
    """)
    
    # 成就表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            achievement_type TEXT NOT NULL,
            achievement_name TEXT NOT NULL,
            earned_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()

# ==================== 用户管理 ====================
def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

# database.py 中的 register_user 函数确认
def register_user(username, password, learning_style, learning_purpose, school=None, grade=None):
    """注册用户"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password, learning_style, learning_purpose, school, grade, level, total_points, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            username, 
            hash_password(password), 
            learning_style, 
            learning_purpose, 
            school, 
            grade,  # 年级字段
            '小学徒', 
            0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"注册失败：{e}")
        return False

def login_user(username, password) -> bool:
    """用户登录"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM users WHERE username = ? AND password = ?
        """, (username, hash_password(password)))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # 更新最后登录时间
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE username = ?
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
            conn.commit()
            conn.close()
            return True
        return False
    except Exception as e:
        print(f"登录失败：{e}")
        return False

def get_user_info(username: str) -> dict:
    """获取用户信息"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "username": user["username"],
                "learning_style": user["learning_style"],
                "learning_purpose": user["learning_purpose"],
                "school": user["school"],
                "grade": user["grade"],
                "level": user["level"],
                "total_points": user["total_points"],
                "created_at": user["created_at"],
                "last_login": user["last_login"]
            }
        return {}
    except Exception as e:
        print(f"获取用户信息失败：{e}")
        return {}

def update_user_profile(username, learning_style, learning_purpose):
    """更新用户配置"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET learning_style = ?, learning_purpose = ? WHERE username = ?
        """, (learning_style, learning_purpose, username))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"更新配置失败：{e}")
        return False

# ==================== 学习记录 ====================
def save_record(username, poem_title, poem_id, user_input, ai_reply, score=None):
    """保存学习记录"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO learning_records (username, poem_id, poem_title, user_input, ai_reply, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username, 
            poem_id, 
            poem_title, 
            user_input, 
            ai_reply, 
            score,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"保存记录失败：{e}")
        return False

def get_user_history(username: str, limit: int = 50) -> list:
    """获取用户学习历史"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM learning_records 
            WHERE username = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (username, limit))
        records = cursor.fetchall()
        conn.close()
        return [dict(row) for row in records]
    except Exception as e:
        print(f"获取历史失败：{e}")
        return []

# ==================== 掌握程度 ====================
def get_mastery(username: str, poem_id: str) -> dict:
    """获取用户对某诗词的掌握程度"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 查询学习记录
        cursor.execute("""
            SELECT COUNT(*) as count, AVG(score) as avg_score 
            FROM learning_records 
            WHERE username = ? AND poem_id = ?
        """, (username, poem_id))
        
        result = cursor.fetchone()
        conn.close()
        
        answer_count = result[0] if result[0] else 0
        avg_score = result[1] if result[1] else 0
        
        # 掌握程度评判逻辑
        if answer_count == 0:
            mastery_level = "未学习"
        elif answer_count >= 8 and avg_score >= 90:
            mastery_level = "精通"
        elif answer_count >= 5 and avg_score >= 75:
            mastery_level = "熟练"
        elif answer_count >= 3 and avg_score >= 60:
            mastery_level = "掌握"
        else:
            # 只要有过学习记录就算学习中
            mastery_level = "学习中"
        
        return {
            "mastery_level": mastery_level,
            "answer_count": answer_count,
            "avg_score": avg_score
        }
    except Exception as e:
        print(f"获取掌握程度失败：{e}")
        return {"mastery_level": "未学习", "answer_count": 0, "avg_score": 0}

# ==================== 排行榜 ====================
# database.py

def get_leaderboard(limit: int = 20, scope: str = "all", current_username: str = None) -> list:
    """获取排行榜"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if scope == "school" and current_username:
            # 先获取当前用户的学校
            cursor.execute("SELECT school FROM users WHERE username = ?", (current_username,))
            user_school = cursor.fetchone()
            
            if user_school and user_school["school"]:
                # 按学校筛选
                cursor.execute("""
                    SELECT username, level, total_points, school, grade,
                           RANK() OVER (ORDER BY total_points DESC) as rank
                    FROM users
                    WHERE school = ?
                    ORDER BY total_points DESC
                    LIMIT ?
                """, (user_school["school"], limit))
            else:
                # 学校为空则返回全部
                cursor.execute("""
                    SELECT username, level, total_points, school, grade,
                           RANK() OVER (ORDER BY total_points DESC) as rank
                    FROM users
                    ORDER BY total_points DESC
                    LIMIT ?
                """, (limit,))
        else:
            cursor.execute("""
                SELECT username, level, total_points, school, grade,
                       RANK() OVER (ORDER BY total_points DESC) as rank
                FROM users
                ORDER BY total_points DESC
                LIMIT ?
            """, (limit,))
        
        users = cursor.fetchall()
        conn.close()
        return [dict(row) for row in users]
    except Exception as e:
        print(f"获取排行榜失败：{e}")
        return []

def get_user_rank(username: str, scope: str = "all") -> int:
    """获取用户排名"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if scope == "all":
            # 全局排名
            cursor.execute("""
                SELECT rank FROM (
                    SELECT username, RANK() OVER (ORDER BY total_points DESC) as rank
                    FROM users
                ) WHERE username = ?
            """, (username,))
        else:
            # 同校排名
            cursor.execute("SELECT school FROM users WHERE username = ?", (username,))
            user_school = cursor.fetchone()
            if user_school and user_school["school"]:
                cursor.execute("""
                    SELECT rank FROM (
                        SELECT username, RANK() OVER (ORDER BY total_points DESC) as rank
                        FROM users
                        WHERE school = ?
                    ) WHERE username = ?
                """, (user_school["school"], username))
            else:
                cursor.execute("""
                    SELECT rank FROM (
                        SELECT username, RANK() OVER (ORDER BY total_points DESC) as rank
                        FROM users
                    ) WHERE username = ?
                """, (username,))
        
        result = cursor.fetchone()
        conn.close()
        return result["rank"] if result else 0
    except Exception as e:
        print(f"获取排名失败：{e}")
        return 0

# ==================== 积分系统 ====================
def add_user_points(username: str, points: int):
    """添加用户积分"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET total_points = total_points + ? WHERE username = ?
        """, (points, username))
        conn.commit()
        
        # 更新等级
        cursor.execute("SELECT total_points FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            total_points = result[0]
            new_level = get_level_by_points(total_points)
            cursor.execute("UPDATE users SET level = ? WHERE username = ?", (new_level, username))
            conn.commit()
            print(f"✅ 积分更新：{username} 当前积分={total_points}, 等级={new_level}")  # 调试日志
        
        conn.close()
        return True
    except Exception as e:
        print(f"添加积分失败：{e}")
        return False

def get_level_by_points(points: int) -> str:
    """根据积分获取等级"""
    if points >= 1000:
        return "大师"
    elif points >= 600:
        return "精通者"
    elif points >= 300:
        return "进阶者"
    elif points >= 100:
        return "学习者"
    else:
        return "小学徒"

# ==================== 成就系统 ====================
def add_achievement(username: str, achievement_type: str, achievement_name: str):
    """添加成就"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 检查是否已获得该成就
        cursor.execute("""
            SELECT * FROM achievements 
            WHERE username = ? AND achievement_type = ?
        """, (username, achievement_type))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO achievements (username, achievement_type, achievement_name, earned_at)
                VALUES (?, ?, ?, ?)
            """, (username, achievement_type, achievement_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        
        conn.close()
        return True
    except Exception as e:
        print(f"添加成就失败：{e}")
        return False

def get_user_achievements(username: str) -> list:
    """获取用户成就"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM achievements 
            WHERE username = ? 
            ORDER BY earned_at DESC
        """, (username,))
        achievements = cursor.fetchall()
        conn.close()
        return [dict(row) for row in achievements]
    except Exception as e:
        print(f"获取成就失败：{e}")
        return []

# ==================== 学习报告 ====================
def generate_learning_report(username: str) -> dict:
    """生成学习报告"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 用户信息
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        # 学习统计
        cursor.execute("""
            SELECT COUNT(*) as total_records, AVG(score) as avg_score 
            FROM learning_records 
            WHERE username = ?
        """, (username,))
        stats = cursor.fetchone()
        
        # 已学诗词数
        cursor.execute("""
            SELECT COUNT(DISTINCT poem_id) as poems_learned 
            FROM learning_records 
            WHERE username = ?
        """, (username,))
        poems_learned = cursor.fetchone()[0]
        
        # 掌握诗词数
        cursor.execute("""
            SELECT poem_id FROM learning_records WHERE username = ?
        """, (username,))
        poem_ids = set(row[0] for row in cursor.fetchall())
        conn.close()
        
        mastered_poems = 0
        for poem_id in poem_ids:
            mastery = get_mastery(username, poem_id)
            if mastery["mastery_level"] in ["掌握", "熟练", "精通"]:
                mastered_poems += 1
        
        # 排名
        rank = get_user_rank(username)
        
        return {
            "username": user["username"] if user else "未知",
            "level": user["level"] if user else "小学徒",
            "total_points": user["total_points"] if user else 0,
            "rank": rank,
            "total_records": stats[0] if stats[0] else 0,
            "avg_score": round(stats[1] if stats[1] else 0, 1),
            "poems_learned": poems_learned,
            "mastered_poems": mastered_poems,
            "created_at": user["created_at"] if user else "未知",
            "last_login": user["last_login"] if user else "未知"
        }
    except Exception as e:
        print(f"生成报告失败：{e}")
        return {}