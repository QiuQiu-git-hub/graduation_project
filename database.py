#数据库与个性化管理
# database.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime # type: ignore
from sqlalchemy.orm import declarative_base, sessionmaker # type: ignore
from datetime import datetime
import hashlib

# 1. 配置 SQLite 数据库
Base = declarative_base()
engine = create_engine('sqlite:///poetry_data.db', echo=False)
Session = sessionmaker(bind=engine)

# 2. 定义数据表结构

class User(Base):
    """用户画像表：存储用户基本信息"""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(100))  # 密码哈希
    learning_style = Column(String(50))  # 对话风格
    learning_purpose = Column(String(100))  # 学习目的
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)

class LearningRecord(Base):
    """学习记录表：存储交互历史"""
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    poem_title = Column(String(100))
    user_input = Column(Text)
    ai_feedback = Column(Text)
    score = Column(Integer, nullable=True)  # 改为可空
    timestamp = Column(DateTime, default=datetime.now)

# 3. 初始化数据库
def init_db():
    Base.metadata.create_all(engine)
def hash_password(password: str) -> str:
    """密码哈希加密"""
    return hashlib.sha256(password.encode()).hexdigest()
def register_user(username: str, password: str, style: str, purpose: str) -> bool:
    """注册用户"""
    session = Session()
    existing = session.query(User).filter_by(username=username).first()
    if existing:
        session.close()
        return False
    user = User(
        username=username,
        password_hash=hash_password(password),
        learning_style=style,
        learning_purpose=purpose
    )
    session.add(user)
    session.commit()
    session.close()
    return True
def login_user(username: str, password: str) -> bool:
    """验证登录"""
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        session.close()
        return False
    if user.password_hash == hash_password(password):
        user.last_login = datetime.now()
        session.commit()
        session.close()
        return True
    session.close()
    return False
def get_user_info(username: str) -> dict:
    """获取用户信息"""
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if user:
        info = {
            "username": user.username,
            "learning_style": user.learning_style,
            "learning_purpose": user.learning_purpose
        }
        session.close()
        return info
    session.close()
    return {}

def update_user_profile(username: str, style: str, purpose: str):
    """更新用户画像"""
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if user:
        user.learning_style = style
        user.learning_purpose = purpose
        session.commit()
    session.close()

def get_or_create_user(username: str, style: str, purpose: str = "兴趣学习"):
    """兼容旧接口的用户创建"""
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        user = User(username=username, learning_style=style, learning_purpose=purpose)
        session.add(user)
        session.commit()
    session.close()
    return user

def save_record(username: str, poem: str, input_text: str, feedback: str, score: int = None):
    session = Session()
    record = LearningRecord(
        username=username,
        poem_title=poem,
        user_input=input_text,
        ai_feedback=feedback,
        score=score  # 直接传入，允许 None
    )
    session.add(record)
    session.commit()
    session.close()

def get_user_history(username: str):
    session = Session()
    records = session.query(LearningRecord).filter_by(username=username).order_by(LearningRecord.timestamp.desc()).all()
    session.close()
    return records
