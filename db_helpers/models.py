import uuid

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, func, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    tg_id = Column(Integer, unique=True)
    selections = relationship("TimeSelection", back_populates="user")
    number_selections = relationship("NumberSelection", back_populates="user")


class TimeSelection(Base):
    __tablename__ = 'time_selections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    time_choice_id = Column(Integer, ForeignKey('time_choices.id', name='fk_time_selection_time_choice'))
    time_choice = relationship("TimeChoice")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="selections")
    timestamp = Column(DateTime, server_default=func.now())


class TimeRange(Base):
    """Группировка по 4 временным отрезкам."""
    __tablename__ = 'time_ranges'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    time_range = Column(String, index=True)
    choices = relationship("TimeChoice", back_populates="time_range")  # Добавлено


class TimeChoice(Base):
    """ Тут лежит время и определение."""
    __tablename__ = 'time_choices'
    id = Column(Integer, primary_key=True, index=True)
    choice = Column(String, index=True)
    interpretation = Column(String)
    time_range_id = Column(Integer, ForeignKey('time_ranges.id'))
    time_range = relationship("TimeRange", back_populates="choices")  # Уже есть


class NumberChoice(Base):
    __tablename__ = "numbers_choices"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, index=True)
    interpretation = Column(String)

    # Связь с NumberSelection
    selections = relationship("NumberSelection", back_populates="number_choice")


class NumberSelection(Base):
    __tablename__ = 'number_selections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    number_choice_id = Column(Integer, ForeignKey('numbers_choices.id'), nullable=False)

    # Связи
    user = relationship("User", back_populates="number_selections")
    number_choice = relationship("NumberChoice")

    # Время выбора (опционально)
    timestamp = Column(DateTime, server_default=func.now())


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
