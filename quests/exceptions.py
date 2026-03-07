# quests/exceptions.py

class QuestNotFoundError(Exception):
    """Квест не найден"""
    pass


class QuestConflictError(Exception):
    """Конфликт данных"""
    pass


class QuestValidationError(Exception):
    """Ошибка валидации"""
    pass