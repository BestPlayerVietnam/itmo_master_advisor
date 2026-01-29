"""
Главный файл запуска приложения
"""
import argparse
import logging

from config import settings

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def parse_data():
    """Парсинг данных с сайтов"""
    from parser.scraper import main as parse_main
    parse_main()


def index_data():
    """Индексация данных в векторное хранилище"""
    from rag.vector_store import VectorStore
    
    store = VectorStore()
    store.clear()
    store.load_and_index_programs()
    logger.info("Data indexed successfully!")


def run_bot():
    """Запуск Telegram-бота"""
    from bot.telegram_bot import run_bot as start_bot
    start_bot()


def main():
    parser = argparse.ArgumentParser(description="ITMO Master Advisor Bot")
    parser.add_argument(
        "command",
        choices=["parse", "index", "run", "all"],
        help="Command to execute"
    )
    
    args = parser.parse_args()
    
    if args.command == "parse":
        parse_data()
    elif args.command == "index":
        index_data()
    elif args.command == "run":
        run_bot()
    elif args.command == "all":
        logger.info("Running full pipeline...")
        parse_data()
        index_data()
        run_bot()


if __name__ == "__main__":
    main()