"""
Рекомендательная система для выбора курсов
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import json
import logging

from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)


class SkillLevel(Enum):
    """Уровни владения навыками"""
    NONE = "none"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class UserSkills:
    """Навыки пользователя"""
    python: SkillLevel = SkillLevel.NONE
    math: SkillLevel = SkillLevel.NONE
    statistics: SkillLevel = SkillLevel.NONE
    ml_basics: SkillLevel = SkillLevel.NONE
    deep_learning: SkillLevel = SkillLevel.NONE
    nlp: SkillLevel = SkillLevel.NONE
    computer_vision: SkillLevel = SkillLevel.NONE
    mlops: SkillLevel = SkillLevel.NONE
    
    @classmethod
    def from_background(cls, background: str) -> "UserSkills":
        """Создание профиля навыков из текстового описания"""
        # Простая эвристика — в реальности можно использовать LLM
        background_lower = background.lower()
        
        skills = cls()
        
        # Python
        if any(word in background_lower for word in ["python", "питон", "программирован"]):
            skills.python = SkillLevel.INTERMEDIATE
        if "senior" in background_lower or "lead" in background_lower:
            skills.python = SkillLevel.ADVANCED
            
        # Математика
        if any(word in background_lower for word in ["математик", "math", "физик", "мехмат"]):
            skills.math = SkillLevel.ADVANCED
            skills.statistics = SkillLevel.INTERMEDIATE
            
        # ML
        if any(word in background_lower for word in ["ml", "machine learning", "машинн"]):
            skills.ml_basics = SkillLevel.INTERMEDIATE
            
        if any(word in background_lower for word in ["data scien", "ds", "аналитик данных"]):
            skills.ml_basics = SkillLevel.INTERMEDIATE
            skills.statistics = SkillLevel.INTERMEDIATE
            
        # Deep Learning
        if any(word in background_lower for word in ["deep learning", "нейронн", "pytorch", "tensorflow"]):
            skills.deep_learning = SkillLevel.INTERMEDIATE
            
        # NLP
        if any(word in background_lower for word in ["nlp", "нлп", "обработка текст", "natural language"]):
            skills.nlp = SkillLevel.INTERMEDIATE
            
        # CV
        if any(word in background_lower for word in ["computer vision", "cv", "компьютерн зрен", "opencv"]):
            skills.computer_vision = SkillLevel.INTERMEDIATE
            
        # MLOps
        if any(word in background_lower for word in ["mlops", "devops", "docker", "kubernetes", "deploy"]):
            skills.mlops = SkillLevel.INTERMEDIATE
            
        return skills


@dataclass
class Course:
    """Информация о курсе"""
    name: str
    program: str
    semester: int
    course_type: str
    credits: int
    description: str = ""
    prerequisites: List[str] = None
    skills_gained: List[str] = None
    difficulty: str = "medium"
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []
        if self.skills_gained is None:
            self.skills_gained = []


@dataclass 
class CourseRecommendation:
    """Рекомендация курса"""
    course: Course
    score: float
    reasoning: str
    priority: int  # 1 = высший приоритет


class CourseRecommender:
    """Рекомендательная система для курсов"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.courses = self._load_courses()
    
    def _load_courses(self) -> List[Course]:
        """Загрузка курсов из JSON файлов"""
        courses = []
        
        for filename in ["ai_program.json", "ai_product_program.json"]:
            filepath = f"{settings.DATA_DIR}/{filename}"
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    program_name = data.get('name', 'Unknown')
                    
                    for course_data in data.get('courses', []):
                        course = Course(
                            name=course_data['name'],
                            program=program_name,
                            semester=course_data.get('semester', 1),
                            course_type=course_data.get('course_type', 'обязательная'),
                            credits=course_data.get('credits', 3),
                            description=course_data.get('description', ''),
                            prerequisites=course_data.get('prerequisites', []),
                            skills_gained=course_data.get('skills', [])
                        )
                        courses.append(course)
                        
            except FileNotFoundError:
                logger.warning(f"File not found: {filepath}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in {filepath}")
        
        # Добавляем дефолтные курсы, если файлы не найдены
        if not courses:
            courses = self._get_default_courses()
            
        return courses
    
    def _get_default_courses(self) -> List[Course]:
        """Дефолтный список курсов"""
        return [
            # AI Program - Обязательные
            Course("Машинное обучение", "AI", 1, "обязательная", 4,
                   "Основы ML: регрессия, классификация, кластеризация",
                   prerequisites=["Python", "Линейная алгебра"],
                   skills_gained=["sklearn", "pandas", "ML pipelines"]),
            
            Course("Глубокое обучение", "AI", 2, "обязательная", 4,
                   "Нейронные сети, CNN, RNN, Transformers",
                   prerequisites=["Машинное обучение"],
                   skills_gained=["PyTorch", "Нейронные сети"]),
            
            Course("Математическая статистика", "AI", 1, "обязательная", 3,
                   "Статистические методы для ML",
                   prerequisites=["Теория вероятностей"],
                   skills_gained=["Статистический анализ", "A/B тесты"]),
            
            Course("MLOps", "AI", 3, "обязательная", 3,
                   "Развёртывание и мониторинг ML-систем",
                   prerequisites=["Машинное обучение", "Docker"],
                   skills_gained=["Docker", "CI/CD", "Model serving"]),
            
            # AI Program - Выборные
            Course("Компьютерное зрение", "AI", 2, "выборная", 3,
                   "Обработка изображений, детекция, сегментация",
                   prerequisites=["Глубокое обучение"],
                   skills_gained=["OpenCV", "CNN", "Object Detection"],
                   difficulty="high"),
            
            Course("Обработка естественного языка", "AI", 2, "выборная", 3,
                   "NLP: токенизация, эмбеддинги, трансформеры",
                   prerequisites=["Глубокое обучение"],
                   skills_gained=["Transformers", "BERT", "Text processing"],
                   difficulty="high"),
            
            Course("Reinforcement Learning", "AI", 3, "выборная", 3,
                   "Обучение с подкреплением",
                   prerequisites=["Глубокое обучение", "Теория вероятностей"],
                   skills_gained=["RL algorithms", "Gym", "Policy optimization"],
                   difficulty="high"),
            
            Course("Генеративные модели", "AI", 3, "выборная", 3,
                   "VAE, GAN, Diffusion models",
                   prerequisites=["Глубокое обучение"],
                   skills_gained=["GANs", "Diffusion", "Image generation"],
                   difficulty="high"),
            
            Course("Big Data", "AI", 2, "выборная", 3,
                   "Spark, распределённые вычисления",
                   prerequisites=["Python", "SQL"],
                   skills_gained=["Spark", "Hadoop", "Distributed computing"]),
            
            # AI Product - Специфичные
            Course("Управление AI-продуктом", "AI Product", 1, "обязательная", 3,
                   "Product management для AI-продуктов",
                   prerequisites=[],
                   skills_gained=["Product thinking", "Roadmap", "Metrics"]),
            
            Course("Дизайн AI-систем", "AI Product", 2, "обязательная", 3,
                   "Проектирование архитектуры ML-систем",
                   prerequisites=["Машинное обучение"],
                   skills_gained=["System design", "ML architecture"]),
            
            Course("AI Ethics", "AI Product", 2, "выборная", 2,
                   "Этика искусственного интеллекта",
                   prerequisites=[],
                   skills_gained=["AI Ethics", "Responsible AI", "Bias detection"]),
        ]
    
    def get_elective_courses(self, program: Optional[str] = None) -> List[Course]:
        """Получение списка выборных курсов"""
        courses = [c for c in self.courses if c.course_type == "выборная"]
        
        if program:
            courses = [c for c in courses if program.lower() in c.program.lower()]
            
        return courses
    
    def recommend_courses(
        self,
        user_background: str,
        interests: List[str],
        program: Optional[str] = None,
        max_recommendations: int = 5
    ) -> List[CourseRecommendation]:
        """
        Рекомендация курсов на основе профиля пользователя
        
        Args:
            user_background: Текстовое описание бэкграунда
            interests: Список интересов
            program: Фильтр по программе (опционально)
            max_recommendations: Максимум рекомендаций
            
        Returns:
            Список рекомендаций с оценками
        """
        # Анализируем навыки пользователя
        user_skills = UserSkills.from_background(user_background)
        
        # Получаем выборные курсы
        electives = self.get_elective_courses(program)
        
        if not electives:
            return []
        
        # Оцениваем каждый курс
        recommendations = []
        
        for course in electives:
            score, reasoning = self._score_course(course, user_skills, interests)
            
            recommendations.append(CourseRecommendation(
                course=course,
                score=score,
                reasoning=reasoning,
                priority=0  # Будет установлен после сортировки
            ))
        
        # Сортируем по score
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        # Устанавливаем приоритеты
        for i, rec in enumerate(recommendations[:max_recommendations]):
            rec.priority = i + 1
        
        return recommendations[:max_recommendations]
    
    def _score_course(
        self,
        course: Course,
        user_skills: UserSkills,
        interests: List[str]
    ) -> tuple[float, str]:
        """
        Оценка релевантности курса для пользователя
        
        Returns:
            (score, reasoning)
        """
        score = 0.0
        reasons = []
        
        # 1. Совпадение с интересами (40% веса)
        interest_score = 0.0
        course_name_lower = course.name.lower()
        course_desc_lower = course.description.lower()
        
        interest_matches = []
        for interest in interests:
            interest_lower = interest.lower()
            if interest_lower in course_name_lower or interest_lower in course_desc_lower:
                interest_score += 0.4
                interest_matches.append(interest)
                
        if interest_matches:
            reasons.append(f"Соответствует интересам: {', '.join(interest_matches)}")
        
        score += min(interest_score, 0.4)  # Максимум 0.4
        
        # 2. Соответствие уровню подготовки (30% веса)
        readiness_score = self._check_prerequisites(course, user_skills)
        score += readiness_score * 0.3
        
        if readiness_score > 0.7:
            reasons.append("Хорошая база для этого курса")
        elif readiness_score < 0.3:
            reasons.append("Может потребоваться дополнительная подготовка")
        
        # 3. Польза для развития (20% веса)
        growth_score = self._calculate_growth_potential(course, user_skills)
        score += growth_score * 0.2
        
        if growth_score > 0.7:
            reasons.append("Поможет освоить новые востребованные навыки")
        
        # 4. Карьерная ценность (10% веса)
        career_score = self._calculate_career_value(course)
        score += career_score * 0.1
        
        if career_score > 0.7:
            reasons.append("Высокая востребованность на рынке")
        
        reasoning = "; ".join(reasons) if reasons else "Общий выборный курс"
        
        return score, reasoning
    
    def _check_prerequisites(self, course: Course, user_skills: UserSkills) -> float:
        """Проверка готовности к курсу"""
        if not course.prerequisites:
            return 1.0
            
        met_prerequisites = 0
        
        for prereq in course.prerequisites:
            prereq_lower = prereq.lower()
            
            if "python" in prereq_lower and user_skills.python.value in ["intermediate", "advanced"]:
                met_prerequisites += 1
            elif "машинн" in prereq_lower or "ml" in prereq_lower:
                if user_skills.ml_basics.value in ["intermediate", "advanced"]:
                    met_prerequisites += 1
            elif "глубок" in prereq_lower or "deep" in prereq_lower:
                if user_skills.deep_learning.value in ["intermediate", "advanced"]:
                    met_prerequisites += 1
            elif "статист" in prereq_lower or "вероятн" in prereq_lower:
                if user_skills.statistics.value in ["intermediate", "advanced"]:
                    met_prerequisites += 1
            elif "алгебр" in prereq_lower or "math" in prereq_lower:
                if user_skills.math.value in ["intermediate", "advanced"]:
                    met_prerequisites += 1
        
        return met_prerequisites / len(course.prerequisites) if course.prerequisites else 1.0
    
    def _calculate_growth_potential(self, course: Course, user_skills: UserSkills) -> float:
        """Оценка потенциала роста"""
        # Чем меньше текущих навыков в области курса — тем выше потенциал роста
        if not course.skills_gained:
            return 0.5
            
        new_skills = 0
        course_skills_text = " ".join(course.skills_gained).lower()
        
        # Проверяем, какие навыки курс даст
        if "nlp" in course_skills_text or "text" in course_skills_text:
            if user_skills.nlp.value in ["none", "beginner"]:
                new_skills += 1
                
        if "cv" in course_skills_text or "vision" in course_skills_text or "image" in course_skills_text:
            if user_skills.computer_vision.value in ["none", "beginner"]:
                new_skills += 1
                
        if "pytorch" in course_skills_text or "нейрон" in course_skills_text:
            if user_skills.deep_learning.value in ["none", "beginner"]:
                new_skills += 1
                
        if "docker" in course_skills_text or "deploy" in course_skills_text:
            if user_skills.mlops.value in ["none", "beginner"]:
                new_skills += 1
        
        return min(new_skills / 2, 1.0)
    
    def _calculate_career_value(self, course: Course) -> float:
        """Оценка карьерной ценности курса"""
        high_value_keywords = [
            "deep learning", "глубокое", "nlp", "computer vision",
            "mlops", "transformer", "llm", "генеративн"
        ]
        
        course_text = f"{course.name} {course.description}".lower()
        
        matches = sum(1 for kw in high_value_keywords if kw in course_text)
        
        return min(matches / 3, 1.0)
    
    def get_study_plan(
        self,
        recommendations: List[CourseRecommendation],
        semesters: int = 4
    ) -> Dict[int, List[Course]]:
        """
        Составление плана обучения по семестрам
        
        Args:
            recommendations: Рекомендованные курсы
            semesters: Количество семестров
            
        Returns:
            Словарь {семестр: [курсы]}
        """
        plan = {i: [] for i in range(1, semesters + 1)}
        
        for rec in recommendations:
            semester = rec.course.semester
            if semester <= semesters:
                plan[semester].append(rec.course)
        
        return plan
    
    def format_recommendations(
        self,
        recommendations: List[CourseRecommendation],
        include_plan: bool = True
    ) -> str:
        """Форматирование рекомендаций в текст"""
        if not recommendations:
            return "К сожалению, не удалось подобрать рекомендации. Попробуйте уточнить ваши интересы."
        
        lines = ["🎯 **Рекомендованные курсы:**\n"]
        
        for rec in recommendations:
            emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rec.priority - 1] if rec.priority <= 5 else "▪️"
            
            lines.append(f"{emoji} **{rec.course.name}**")
            lines.append(f"   📍 Программа: {rec.course.program}")
            lines.append(f"   📅 Семестр: {rec.course.semester}")
            lines.append(f"   💡 {rec.reasoning}")
            lines.append(f"   📊 Оценка соответствия: {rec.score:.0%}")
            lines.append("")
        
        if include_plan:
            plan = self.get_study_plan(recommendations)
            
            lines.append("\n📚 **План изучения по семестрам:**\n")
            for semester, courses in plan.items():
                if courses:
                    lines.append(f"**Семестр {semester}:**")
                    for course in courses:
                        lines.append(f"  • {course.name}")
                    lines.append("")
        
        return "\n".join(lines)
    
    async def get_llm_recommendations(
        self,
        user_background: str,
        interests: List[str],
        available_courses: List[Course]
    ) -> str:
        """
        Получение рекомендаций через LLM для более персонализированного ответа
        """
        courses_text = "\n".join([
            f"- {c.name} (семестр {c.semester}, {c.course_type}): {c.description}"
            for c in available_courses
        ])
        
        prompt = f"""
        Пользователь хочет получить рекомендации по выбору курсов.
        
        Бэкграунд пользователя: {user_background}
        Интересы: {', '.join(interests)}
        
        Доступные выборные курсы:
        {courses_text}
        
        Дай персонализированные рекомендации:
        1. Какие 3-5 курсов лучше всего подойдут этому студенту?
        2. В каком порядке их лучше изучать?
        3. Какие навыки поможет развить каждый курс?
        4. Как это поможет в карьере?
        
        Учитывай уровень подготовки студента.
        """
        
        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "Ты — консультант по образовательным программам в области AI."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        
        return response.choices[0].message.content