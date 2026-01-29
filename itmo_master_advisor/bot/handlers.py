"""
Обработчики команд и сообщений Telegram-бота
"""
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters
)
import logging

from bot.states import DialogState, UserProfile
from rag.retriever import RAGRetriever
from prompts.system_prompts import ONBOARDING_PROMPT

logger = logging.getLogger(__name__)

# Глобальное хранилище профилей пользователей
user_profiles: dict[int, UserProfile] = {}

# Инициализация RAG
rag = RAGRetriever()


def get_user_profile(user_id: int) -> UserProfile:
    """Получение или создание профиля пользователя"""
    if user_id not in user_profiles:
        user_profiles[user_id] = UserProfile(user_id=user_id)
    return user_profiles[user_id]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    profile.state = DialogState.START
    
    await update.message.reply_text(
        ONBOARDING_PROMPT,
        reply_markup=ReplyKeyboardMarkup(
            [
                ["🎓 Сравнить программы"],
                ["📚 Помощь с выбором курсов"],
                ["❓ Задать вопрос"]
            ],
            resize_keyboard=True
        )
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    help_text = """
🤖 **Команды бота:**

/start - Начать диалог
/compare - Сравнить программы AI и AI Product
/recommend - Получить рекомендации по курсам
/profile - Показать/обновить профиль
/reset - Сбросить профиль
/help - Показать эту справку

💡 **Примеры вопросов:**
- Какие курсы есть на программе AI?
- Чем отличается AI от AI Product?
- Какие выборные курсы взять, если интересует NLP?
- Какой бэкграунд нужен для поступления?
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сравнение программ"""
    await update.message.reply_text("🔄 Анализирую программы...")
    
    try:
        comparison = rag.compare_programs()
        await update.message.reply_text(comparison)
    except Exception as e:
        logger.error(f"Error comparing programs: {e}")
        await update.message.reply_text(
            "Произошла ошибка при сравнении программ. Попробуйте позже."
        )


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рекомендации по курсам"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    if not profile.is_profile_complete():
        profile.state = DialogState.COLLECTING_BACKGROUND
        await update.message.reply_text(
            "Чтобы дать персональные рекомендации, мне нужно узнать о тебе больше.\n\n"
            "Расскажи о своём бэкграунде (образование, опыт работы с программированием/ML):",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    await update.message.reply_text("🔄 Подбираю курсы...")
    
    try:
        recommendations = rag.get_course_recommendations(
            user_background=profile.background,
            interests=profile.interests or ["машинное обучение"]
        )
        await update.message.reply_text(recommendations)
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        await update.message.reply_text(
            "Произошла ошибка при подборе рекомендаций. Попробуйте позже."
        )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    
    profile_text = f"""
👤 **Твой профиль:**

📚 Бэкграунд: {profile.background or 'Не указан'}
🎯 Интересы: {', '.join(profile.interests) if profile.interests else 'Не указаны'}
💼 Опыт: {profile.experience or 'Не указан'}
🎓 Предпочитаемая программа: {profile.preferred_program or 'Не выбрана'}

Чтобы обновить профиль, используй /reset и начни заново.
    """
    await update.message.reply_text(profile_text, parse_mode='Markdown')


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс профиля"""
    user_id = update.effective_user.id
    user_profiles[user_id] = UserProfile(user_id=user_id)
    
    await update.message.reply_text(
        "✅ Профиль сброшен. Используй /start чтобы начать заново."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.effective_user.id
    profile = get_user_profile(user_id)
    message_text = update.message.text
    
    # Обработка кнопок меню
    if message_text == "🎓 Сравнить программы":
        return await compare_command(update, context)
    elif message_text == "📚 Помощь с выбором курсов":
        return await recommend_command(update, context)
    elif message_text == "❓ Задать вопрос":
        await update.message.reply_text(
            "Задай свой вопрос о программах AI или AI Product:",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Обработка состояний сбора информации
    if profile.state == DialogState.COLLECTING_BACKGROUND:
        profile.background = message_text
        profile.state = DialogState.COLLECTING_INTERESTS
        
        await update.message.reply_text(
            "Отлично! Теперь расскажи, что тебя интересует в AI?\n"
            "(например: компьютерное зрение, NLP, reinforcement learning, MLOps)",
            reply_markup=ReplyKeyboardMarkup(
                [
                    ["Computer Vision", "NLP"],
                    ["Deep Learning", "MLOps"],
                    ["Reinforcement Learning", "Generative AI"],
                    ["Пропустить"]
                ],
                resize_keyboard=True
            )
        )
        return
    
    elif profile.state == DialogState.COLLECTING_INTERESTS:
        if message_text != "Пропустить":
            profile.interests = [i.strip() for i in message_text.replace(",", " ").split()]
        profile.state = DialogState.READY
        
        await update.message.reply_text(
            "Спасибо! Теперь я могу давать персональные рекомендации.\n\n"
            "Задай вопрос о программах или используй кнопки меню:",
            reply_markup=ReplyKeyboardMarkup(
                [
                    ["🎓 Сравнить программы"],
                    ["📚 Помощь с выбором курсов"],
                    ["❓ Задать вопрос"]
                ],
                resize_keyboard=True
            )
        )
        return
    
    # Обычный вопрос — обрабатываем через RAG
    await update.message.reply_text("🔄 Думаю над ответом...")
    
    try:
        answer = rag.get_answer(
            query=message_text,
            user_context=profile.to_context(),
            check_relevance=True
        )
        await update.message.reply_text(answer)
        
        # Сохраняем в историю
        profile.conversation_history.append({
            "role": "user",
            "content": message_text
        })
        profile.conversation_history.append({
            "role": "assistant", 
            "content": answer
        })
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке вопроса. Попробуйте переформулировать."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")