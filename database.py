#数据库与个性化管理
# database.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

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
    learning_style = Column(String(50))  # 例如：喜欢"故事化"还是"学术化"
    created_at = Column(DateTime, default=datetime.now)

class LearningRecord(Base):
    """学习记录表：存储交互历史"""
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    poem_title = Column(String(100))
    user_input = Column(Text)
    ai_feedback = Column(Text)
    score = Column(Integer)  # 智能评分 (0-100)
    timestamp = Column(DateTime, default=datetime.now)

# 3. 初始化数据库
def init_db():
    Base.metadata.create_all(engine)

# 4. 数据库操作函数
def get_or_create_user(username, style="标准模式"):
    session = Session()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        user = User(username=username, learning_style=style)
        session.add(user)
        session.commit()
    session.close()
    return user

def save_record(username, poem, input_text, feedback, score):
    session = Session()
    record = LearningRecord(
        username=username, 
        poem_title=poem, 
        user_input=input_text, 
        ai_feedback=feedback, 
        score=score
    )
    session.add(record)
    session.commit()
    session.close()

def get_user_history(username):
    session = Session()
    records = session.query(LearningRecord).filter_by(username=username).order_by(LearningRecord.timestamp.desc()).all()
    session.close()
    return records