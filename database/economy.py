from datetime import datetime, timedelta
from database.db import SessionLocal
from database.models import User, ChatMember
from config import (
    START_BALANCE,
    GROW_COOLDOWN_HOURS, DIG_COOLDOWN_HOURS,
    FAP_COOLDOWN_MINUTES, FAP_MAX_PER_DAY,
    GROW_COOLDOWN_HOURS_VIP, DIG_COOLDOWN_HOURS_VIP,
    FAP_COOLDOWN_MINUTES_VIP, FAP_MAX_PER_DAY_VIP,
)


def get_or_create_user(db, user_id: int, username: str = None) -> User:
    """Глобальный пользователь (без привязки к чату)"""
    user = db.query(User).filter_by(user_id=user_id).first()
    if not user:
        user = User(
            user_id=user_id,
            username=username,
            balance=START_BALANCE
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif username and username != user.username:
        user.username = username
        db.commit()
    return user


def get_or_create_chat_member(db, user_id: int, chat_id: int) -> ChatMember:
    """Статистика игр в конкретном чате"""
    member = db.query(ChatMember).filter_by(user_id=user_id, chat_id=chat_id).first()
    if not member:
        member = ChatMember(user_id=user_id, chat_id=chat_id)
        db.add(member)
        db.commit()
        db.refresh(member)
    return member


def transfer_money(db, from_user: User, to_user: User, amount: int) -> tuple:
    if amount <= 0:
        return False, "Сумма должна быть положительной"
    if from_user.balance < amount:
        return False, f"❌ Недостаточно монет! Баланс: {from_user.balance}"

    from_user.balance -= amount
    to_user.balance += amount
    db.commit()
    return True, f"✅ Переведено {amount} монет пользователю @{to_user.username}"


def check_cooldown(user: User, action: str, hours: int = 0, minutes: int = 0) -> tuple:
    """Возвращает (можно_использовать, осталось_секунд_или_0) с учётом VIP"""
    now = datetime.utcnow()
    last_attr = f'last_{action}'
    last_time = getattr(user, last_attr)

    # Если VIP активен, используем VIP-кулдауны
    is_vip = user.is_vip and user.vip_until and user.vip_until > now
    if action == 'grow':
        hours = GROW_COOLDOWN_HOURS_VIP if is_vip else GROW_COOLDOWN_HOURS
    elif action == 'dig':
        hours = DIG_COOLDOWN_HOURS_VIP if is_vip else DIG_COOLDOWN_HOURS
    elif action == 'fap':
        minutes = FAP_COOLDOWN_MINUTES_VIP if is_vip else FAP_COOLDOWN_MINUTES

    if last_time:
        delta = timedelta(hours=hours, minutes=minutes)
        remaining = delta - (now - last_time)
        if remaining.total_seconds() > 0:
            return False, int(remaining.total_seconds())
    return True, 0


def update_cooldown(db, user: User, action: str):
    """Обновляет время последнего действия, для фапа дополнительно учитывает дневной лимит"""
    setattr(user, f'last_{action}', datetime.utcnow())

    if action == 'fap':
        now = datetime.utcnow()
        if not user.fap_day_reset or now.date() > user.fap_day_reset.date():
            user.faps_today = 0
            user.fap_day_reset = now
        user.faps_today += 1
        user.faps += 1

    db.commit()


def check_ban(user: User) -> bool:
    if user.banned_until and user.banned_until > datetime.utcnow():
        return True
    return False
