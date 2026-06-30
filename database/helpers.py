from telegram.ext import CallbackContext
from datetime import datetime
from database.models import User


async def delete_message(context: CallbackContext):
    """Удаляет сообщение по job.data['chat_id'] и job.data['message_id']"""
    try:
        await context.bot.delete_message(
            chat_id=context.job.data['chat_id'],
            message_id=context.job.data['message_id']
        )
    except:
        pass


async def schedule_message_deletion(context: CallbackContext, chat_id: int, message_id: int, delay_seconds: int):
    """Планирует удаление сообщения"""
    context.job_queue.run_once(
        delete_message,
        delay_seconds,
        data={'chat_id': chat_id, 'message_id': message_id}
    )


def is_registered(user: User) -> bool:
    """Проверяет, выбран ли пол (зарегистрирован ли пользователь)"""
    return user.gender is not None


def vip_mention(user) -> str:
    """HTML-упоминание пользователя с иконкой VIP, если активен"""
    from datetime import datetime
    name = user.username or f"user{user.user_id}"
    if user.is_vip and user.vip_until and user.vip_until > datetime.utcnow():
        return f'<a href="tg://user?id={user.user_id}">💎VIP💎 {name}</a>'
    else:
        return f'<a href="tg://user?id={user.user_id}">{name}</a>'