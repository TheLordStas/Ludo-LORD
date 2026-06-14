from database.db import SessionLocal
from database.models import User
from datetime import datetime, timedelta


def get_or_create_user(db, user_id: int, chat_id: int, username: str = None) -> User:
    user = db.query(User).filter_by(user_id=user_id, chat_id=chat_id).first()
    if not user:
        user = User(
            user_id=user_id,
            chat_id=chat_id,
            username=username,
            balance=5000
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif username and username != user.username:
        user.username = username
        db.commit()
    return user


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
    now = datetime.utcnow()
    last_attr = f'last_{action}'
    last_time = getattr(user, last_attr)

    if last_time:
        delta = timedelta(hours=hours, minutes=minutes)
        remaining = delta - (now - last_time)
        if remaining.total_seconds() > 0:
            total_seconds = int(remaining.total_seconds())
            return False, total_seconds
    return True, 0


def update_cooldown(db, user: User, action: str):
    setattr(user, f'last_{action}', datetime.utcnow())

    if action == 'fap':
        now = datetime.utcnow()
        if not user.fap_day_reset or now.date() > user.fap_day_reset.date():
            user.faps_today = 0
            user.fap_day_reset = now
        user.faps_today += 1
        user.faps += 1

    db.commit()
