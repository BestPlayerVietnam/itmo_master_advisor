"""
RAG Retriever с LLM-генерацией ответов и интеграцией рекомендательной системы
"""
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import logging

from config import settings
from rag.vector_store import VectorStore
from recommender.course_recommender import CourseRecommender
from prompts.system_prompts import (
    SYSTEM_PROMPT,
    RELEVANCE_CHECK_PROMPT,
    RECOMMENDATION_PROMPT
)

logger = logging.getLogger(__name__)


class RAGRetriever:
    """RAG-система для ответов на вопросы с рекомендациями курсов"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.recommender = CourseRecommender()
        self.conversation_cache: Dict[int, List[Dict]] = {}
    
    def check_relevance(self, query: str) -> Tuple[bool, str]:
        """
        Проверка релевантности вопроса тематике магистратур ИТМО
        
        Args:
            query: Вопрос пользователя
            
        Returns:
            (is_relevant, rejection_message)
        """
        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": RELEVANCE_CHECK_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            answer = response.choices[0].message.content.strip().lower()
            
            if "да" in answer or "yes" in answer or "релевант" in answer:
                return True, ""
            else:
                rejection_message = (
                    "Извините, я могу отвечать только на вопросы о магистерских "
                    "программах ИТМО по направлениям AI и AI Product.\n\n"
                    "Примеры вопросов, на которые я могу ответить:\n"
                    "• Какие курсы есть на программе AI?\n"
                    "• Чем отличаются программы AI и AI Product?\n"
                    "• Какие выборные дисциплины лучше взять для NLP?\n"
                    "• Какие требования для поступления?"
                )
                return False, rejection_message
                
        except Exception as e:
            logger.error(f"Error checking relevance: {e}")
            # В случае ошибки пропускаем проверку
            return True, ""
    
    def get_answer(
        self,
        query: str,
        user_context: Optional[Dict] = None,
        user_id: Optional[int] = None,
        check_relevance: bool = True
    ) -> str:
        """
        Получение ответа на вопрос с использованием RAG
        
        Args:
            query: Вопрос пользователя
            user_context: Контекст пользователя (бэкграунд, интересы)
            user_id: ID пользователя для кэширования истории
            check_relevance: Проверять ли релевантность вопроса
            
        Returns:
            Ответ на вопрос
        """
        # Проверяем релевантность
        if check_relevance:
            is_relevant, rejection_message = self.check_relevance(query)
            if not is_relevant:
                return rejection_message
        
        # Ищем релевантные документы
        try:
            relevant_docs = self.vector_store.search(query)
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            relevant_docs = []
        
        # Формируем контекст из найденных документов
        context = self._format_context(relevant_docs)
        
        # Добавляем информацию о пользователе
        user_info = self._format_user_info(user_context)
        
        # Получаем историю диалога
        conversation_history = []
        if user_id and user_id in self.conversation_cache:
            conversation_history = self.conversation_cache[user_id][-6:]  # Последние 3 обмена
        
        # Формируем сообщения для LLM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + user_info}
        ]
        
        # Добавляем историю диалога
        messages.extend(conversation_history)
        
        # Добавляем текущий вопрос с контекстом
        current_message = f"""
Контекст из базы знаний:
{context}

Вопрос пользователя: {query}

Ответь на вопрос, используя информацию из контекста. Если информации недостаточно, честно скажи об этом.
"""
        messages.append({"role": "user", "content": current_message})
        
        # Генерируем ответ
        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=settings.TEMPERATURE,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            # Сохраняем в историю
            if user_id:
                if user_id not in self.conversation_cache:
                    self.conversation_cache[user_id] = []
                self.conversation_cache[user_id].append({"role": "user", "content": query})
                self.conversation_cache[user_id].append({"role": "assistant", "content": answer})
                
                # Ограничиваем размер кэша
                if len(self.conversation_cache[user_id]) > 20:
                    self.conversation_cache[user_id] = self.conversation_cache[user_id][-20:]
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Произошла ошибка при генерации ответа. Пожалуйста, попробуйте ещё раз."
    
    def get_course_recommendations(
        self,
        user_background: str,
        interests: List[str],
        program: Optional[str] = None,
        use_llm: bool = True
    ) -> str:
        """
        Получение персонализированных рекомендаций по курсам
        
        Args:
            user_background: Описание бэкграунда пользователя
            interests: Список интересов
            program: Фильтр по программе (опционально)
            use_llm: Использовать ли LLM для дополнительной персонализации
            
        Returns:
            Форматированные рекомендации
        """
        # Получаем рекомендации через рекомендательную систему
        recommendations = self.recommender.recommend_courses(
            user_background=user_background,
            interests=interests,
            program=program,
            max_recommendations=5
        )
        
        if not recommendations:
            return self._get_fallback_recommendations(interests, program)
        
        # Форматируем базовые рекомендации
        base_recommendations = self.recommender.format_recommendations(
            recommendations, 
            include_plan=True
        )
        
        # Опционально обогащаем через LLM
        if use_llm:
            try:
                enriched = self._enrich_recommendations_with_llm(
                    base_recommendations,
                    user_background,
                    interests
                )
                return enriched
            except Exception as e:
                logger.error(f"Error enriching recommendations: {e}")
                return base_recommendations
        
        return base_recommendations
    
    def _enrich_recommendations_with_llm(
        self,
        base_recommendations: str,
        user_background: str,
        interests: List[str]
    ) -> str:
        """Обогащение рекомендаций через LLM"""
        
        prompt = f"""
На основе профиля пользователя и базовых рекомендаций, дай развёрнутый персонализированный совет.

Профиль пользователя:
- Бэкграунд: {user_background}
- Интересы: {', '.join(interests)}

Базовые рекомендации системы:
{base_recommendations}

Дополни рекомендации:
1. Объясни, почему именно эти курсы подходят данному студенту
2. Дай советы по подготовке к сложным курсам
3. Укажи, какие навыки помогут в карьере
4. Предложи дополнительные ресурсы для самостоятельного изучения (если уместно)

Сохрани структуру и форматирование базовых рекомендаций, дополнив их.
"""
        
        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    
    def _get_fallback_recommendations(
        self,
        interests: List[str],
        program: Optional[str] = None
    ) -> str:
        """Запасные рекомендации через поиск в векторной базе"""
        
        # Ищем информацию о выборных курсах
        query = f"выборные курсы элективы {' '.join(interests)}"
        if program:
            query += f" программа {program}"
        
        try:
            courses = self.vector_store.search(query, top_k=10)
            context = self._format_context(courses)
            
            prompt = RECOMMENDATION_PROMPT.format(
                background="Не указан",
                interests=", ".join(interests) if interests else "Общие",
                courses_context=context
            )
            
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.TEMPERATURE,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in fallback recommendations: {e}")
            return (
                "К сожалению, не удалось получить рекомендации. "
                "Попробуйте уточнить ваши интересы или задать конкретный вопрос о курсах."
            )
    
    def compare_programs(self) -> str:
        """
        Сравнение программ AI и AI Product
        
        Returns:
            Форматированное сравнение программ
        """
        try:
            # Получаем информацию об обеих программах
            ai_docs = self.vector_store.search(
                "программа AI машинное обучение курсы",
                top_k=5
            )
            
            product_docs = self.vector_store.search(
                "программа AI Product продукт менеджмент",
                top_k=5
            )
            
            context = f"""
Информация о программе "AI" (Искусственный интеллект):
{self._format_context(ai_docs)}

---

Информация о программе "AI Product" (AI в продуктовой разработке):
{self._format_context(product_docs)}
"""
            
            comparison_prompt = """
На основе предоставленной информации сравни две магистерские программы ИТМО.

Структура ответа:
1. **Краткое описание каждой программы** (2-3 предложения)

2. **Ключевые различия** (таблица или список):
   - Фокус обучения
   - Основные курсы
   - Целевая аудитория
   - Карьерные траектории

3. **Кому подходит программа "AI":**
   - Профиль идеального кандидата
   - Необходимый бэкграунд

4. **Кому подходит программа "AI Product":**
   - Профиль идеального кандидата
   - Необходимый бэкграунд

5. **Рекомендация:** как выбрать между программами

Используй эмодзи для наглядности.
"""
            
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{context}\n\n{comparison_prompt}"}
                ],
                temperature=settings.TEMPERATURE,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error comparing programs: {e}")
            return self._get_fallback_comparison()
    
    def _get_fallback_comparison(self) -> str:
        """Запасное сравнение программ"""
        return """
🎓 **Сравнение магистерских программ ИТМО**

**AI (Искусственный интеллект)**
• Фокус: глубокое погружение в ML/DL, исследования
• Для кого: разработчики, исследователи, будущие ML-инженеры
• Ключевые курсы: Deep Learning, Computer Vision, NLP, RL

**AI Product (AI в продуктовой разработке)**
• Фокус: применение AI в продуктах, менеджмент AI-проектов
• Для кого: продакт-менеджеры, предприниматели, техлиды
• Ключевые курсы: Управление AI-продуктом, Дизайн AI-систем, ML + бизнес

**Как выбрать:**
→ Хотите строить модели и проводить исследования? → **AI**
→ Хотите создавать продукты на основе AI и управлять командами? → **AI Product**

Для более детальной информации задайте конкретный вопрос!
"""
    
    def get_admission_info(self, program: Optional[str] = None) -> str:
        """
        Получение информации о поступлении
        
        Args:
            program: Название программы (опционально)
            
        Returns:
            Информация о поступлении
        """
        query = "требования поступление документы экзамены"
        if program:
            query += f" {program}"
        
        try:
            docs = self.vector_store.search(query, top_k=5)
            context = self._format_context(docs)
            
            prompt = f"""
На основе контекста расскажи о требованиях для поступления на магистерские программы.

Контекст:
{context}

Структура ответа:
1. Общие требования
2. Необходимые документы
3. Вступительные испытания (если есть)
4. Сроки подачи документов
5. Полезные ссылки

Если какой-то информации нет в контексте, укажи это и дай общие рекомендации.
"""
            
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.TEMPERATURE,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error getting admission info: {e}")
            return (
                "Для получения актуальной информации о поступлении рекомендую "
                "посетить официальные страницы программ:\n\n"
                "• AI: https://abit.itmo.ru/program/master/ai\n"
                "• AI Product: https://abit.itmo.ru/program/master/ai_product"
            )
    
    def clear_user_history(self, user_id: int) -> None:
        """Очистка истории диалога пользователя"""
        if user_id in self.conversation_cache:
            del self.conversation_cache[user_id]
    
    def _format_context(self, documents: List[Dict]) -> str:
        """
        Форматирование контекста из найденных документов
        
        Args:
            documents: Список документов из векторного хранилища
            
        Returns:
            Отформатированный контекст
        """
        if not documents:
            return "Релевантная информация не найдена в базе знаний."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            source_info = ""
            if metadata.get('program'):
                source_info = f"[Программа: {metadata['program']}]"
            if metadata.get('course'):
                source_info += f" [Курс: {metadata['course']}]"
            
            context_parts.append(f"{source_info}\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _format_user_info(self, user_context: Optional[Dict]) -> str:
        """
        Форматирование информации о пользователе для системного промпта
        
        Args:
            user_context: Контекст пользователя
            
        Returns:
            Отформатированная строка с информацией
        """
        if not user_context:
            return ""
        
        user_info_parts = ["\n\nИнформация о пользователе:"]
        
        if user_context.get('background'):
            user_info_parts.append(f"- Бэкграунд: {user_context['background']}")
        
        if user_context.get('interests'):
            interests = user_context['interests']
            if isinstance(interests, list):
                interests = ', '.join(interests)
            user_info_parts.append(f"- Интересы: {interests}")
        
        if user_context.get('experience'):
            user_info_parts.append(f"- Опыт: {user_context['experience']}")
        
        if user_context.get('preferred_program'):
            user_info_parts.append(f"- Предпочитаемая программа: {user_context['preferred_program']}")
        
        if len(user_info_parts) > 1:
            user_info_parts.append("\nУчитывай эту информацию при ответе, давая персонализированные рекомендации.")
            return "\n".join(user_info_parts)
        
        return ""