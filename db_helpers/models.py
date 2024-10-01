from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///mydatabase.db"

engine = create_engine(DATABASE_URL, echo=True)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    tg_id = Column(String, unique=True)
    selections = relationship("TimeSelection", back_populates="user")


class TimeSelection(Base):
    __tablename__ = 'time_selections'

    id = Column(Integer, primary_key=True, index=True)
    time_choice_id = Column(Integer, ForeignKey('time_choices.id', name='fk_time_selection_time_choice'))
    time_choice = relationship("TimeChoice")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="selections")
    timestamp = Column(DateTime, server_default=func.now())


class TimeRange(Base):
    __tablename__ = 'time_ranges'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    time_range = Column(String, index=True)
    choices = relationship("TimeChoice", back_populates="time_range")  # Добавлено


class TimeChoice(Base):
    __tablename__ = 'time_choices'
    id = Column(Integer, primary_key=True, index=True)
    choice = Column(String, index=True)
    interpretation = Column(String)
    time_range_id = Column(Integer, ForeignKey('time_ranges.id'))
    time_range = relationship("TimeRange", back_populates="choices")  # Уже есть


# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание всех таблиц в базе данных
Base.metadata.create_all(bind=engine)
