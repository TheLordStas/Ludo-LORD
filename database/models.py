from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)

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

    gender = Column(String, nullable=True)
    is_vip = Column(Boolean, default=False)
    vip_until = Column(DateTime, nullable=True)

    shovel_level = Column(Integer, default=1)
    lube_count = Column(Integer, default=0)
    fertilizer_count = Column(Integer, default=0)
    fertilizer_used_this_grow = Column(Boolean, default=False)

    chat_memberships = relationship('ChatMember', back_populates='user')


class ChatMember(Base):
    __tablename__ = 'chat_members'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    chat_id = Column(BigInteger, nullable=False)

    games_played = Column(Integer, default=0)
    total_bets = Column(Integer, default=0)
    total_won = Column(Integer, default=0)
    total_lost = Column(Integer, default=0)
    joined_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='chat_memberships')


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
    created_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)


class TradeGame(Base):
    __tablename__ = 'trade_games'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    message_id = Column(Integer, nullable=True)
    bet = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)  # 10, 30, 60
    result_multiplier = Column(Float, nullable=True)  # коэффициент по окончании
    status = Column(String, default='active')   # active / finished / cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
