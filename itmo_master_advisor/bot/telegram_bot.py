"""
Основной модуль Telegram-бота
"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from config import settings
from bot.handlers import (
    start_command,
    help_command,
    compare_command,
    recommend_command,
    profile_command,
    reset_command,
    handle_message,
    error_handler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_bot() -> Application:
    """Создание и настройка бота"""
    
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("compare", compare_command))
    application.add_handler(CommandHandler("recommend", recommend_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    return application


def run_bot():
    """Запуск бота"""
    logger.info("Starting bot...")
    
    application = create_bot()
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    run_bot()