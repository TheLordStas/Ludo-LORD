from functools import wraps
from handlers.registration import require_registration


def registration_required(handler):
    """Декоратор для проверки выбора пола перед выполнением команды"""
    @wraps(handler)
    async def wrapper(update, context, *args, **kwargs):
        if not await require_registration(update, context):
            return  # пол не выбран, отправлено меню выбора
        return await handler(update, context, *args, **kwargs)
    return wrapper
