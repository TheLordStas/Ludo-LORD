from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Float, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String, nullable=True)
    chat_id = Column(BigInteger, nullable=False)

    balance = Column(Integer, default=5000)
    cactus = Column(Float, default=0.0)
    faps = Column(Integer, default=0)

    games_played = Column(Integer, default=0)
    total_bets = Column(Integer, default=0)
    total_won = Column(Integer, default=0)
    total_lost = Column(Integer, default=0)

    banned_until = Column(DateTime, nullable=True)

    last_grow = Column(DateTime, nullable=True)
    last_dig = Column(DateTime, nullable=True)
    last_fap = Column(DateTime, nullable=True)
    faps_today = Column(Integer, default=0)
    fap_day_reset = Column(DateTime, nullable=True)


class RouletteHistory(Base):
    __tablename__ = 'roulette_history'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    number = Column(Integer, nullable=False)
    color = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DiceDuel(Base):
    __tablename__ = 'dice_duels'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    challenger_id = Column(BigInteger, nullable=False)
    opponent_id = Column(BigInteger, nullable=False)
    message_id = Column(Integer, nullable=True)
    amount = Column(Integer, nullable=False)
    status = Column(String, default='pending')


class MineGame(Base):
    __tablename__ = 'mine_games'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    message_id = Column(Integer, nullable=True)
    bet = Column(Integer, nullable=False)
    multiplier = Column(Float, default=0.8)
    field = Column(String, nullable=False)
    revealed = Column(String, default='[]')
    apples_found = Column(Integer, default=0)
    status = Column(String, default='active')
