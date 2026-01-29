"""
Состояния диалога для Telegram-бота
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict


class DialogState(Enum):
    """Состояния диалога"""
    START = auto()
    COLLECTING_BACKGROUND = auto()
    COLLECTING_INTERESTS = auto()
    COLLECTING_EXPERIENCE = auto()
    READY = auto()
    AWAITING_QUESTION = auto()


@dataclass
class UserProfile:
    """Профиль пользователя"""
    user_id: int
    background: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    experience: Optional[str] = None
    preferred_program: Optional[str] = None
    state: DialogState = DialogState.START
    conversation_history: List[Dict] = field(default_factory=list)
    
    def to_context(self) -> Dict:
        """Преобразование в контекст для RAG"""
        return {
            "background": self.background,
            "interests": self.interests,
            "experience": self.experience,
            "preferred_program": self.preferred_program
        }
    
    def is_profile_complete(self) -> bool:
        """Проверка заполненности профиля"""
        return bool(self.background)