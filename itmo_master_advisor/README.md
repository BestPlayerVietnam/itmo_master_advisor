# ITMO Master Advisor Bot 🎓🤖

Telegram-бот для помощи абитуриентам в выборе между магистерскими программами ИТМО:
- [AI](https://abit.itmo.ru/program/master/ai)
- [AI Product](https://abit.itmo.ru/program/master/ai_product)

## Возможности

✅ Сравнение программ AI и AI Product
✅ Персональные рекомендации по выбору курсов
✅ Ответы на вопросы по учебным планам
✅ Учёт бэкграунда пользователя
✅ Фильтрация нерелевантных вопросов

## Архитектура

- **Parser**: Selenium + BeautifulSoup для парсинга сайтов
- **RAG**: ChromaDB + OpenAI Embeddings + GPT-4
- **Bot**: python-telegram-bot

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/your-repo/itmo-master-advisor.git
cd itmo-master-advisor

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Заполните TELEGRAM_BOT_TOKEN и OPENAI_API_KEY в .env