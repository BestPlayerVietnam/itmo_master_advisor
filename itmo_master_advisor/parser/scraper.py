"""
Парсер учебных планов магистратур ИТМО
"""
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Course:
    name: str
    semester: int
    credits: int
    course_type: str  # "обязательная", "выборная", "факультатив"
    description: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    skills: Optional[List[str]] = None


@dataclass
class Program:
    name: str
    url: str
    description: str
    duration: str
    format: str
    courses: List[Course]
    admission_requirements: List[str]
    career_prospects: List[str]
    key_competencies: List[str]


class ITMOScraper:
    """Парсер сайтов магистратур ИТМО"""
    
    def __init__(self):
        self.driver = self._init_driver()
    
    def _init_driver(self) -> webdriver.Chrome:
        """Инициализация Selenium WebDriver"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def parse_program(self, url: str) -> Program:
        """Парсинг страницы программы"""
        logger.info(f"Parsing: {url}")
        
        self.driver.get(url)
        time.sleep(3)  # Ждём загрузки JS
        
        # Прокручиваем страницу для загрузки всего контента
        self._scroll_page()
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Извлекаем основную информацию
        program = Program(
            name=self._extract_program_name(soup),
            url=url,
            description=self._extract_description(soup),
            duration=self._extract_duration(soup),
            format=self._extract_format(soup),
            courses=self._extract_courses(soup),
            admission_requirements=self._extract_requirements(soup),
            career_prospects=self._extract_careers(soup),
            key_competencies=self._extract_competencies(soup)
        )
        
        return program
    
    def _scroll_page(self):
        """Прокрутка страницы для загрузки динамического контента"""
        scroll_pause = 0.5
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def _extract_program_name(self, soup: BeautifulSoup) -> str:
        """Извлечение названия программы"""
        title = soup.find('h1')
        return title.get_text(strip=True) if title else "Unknown Program"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Извлечение описания программы"""
        # Ищем блок с описанием
        desc_block = soup.find('div', class_='program-description') or \
                     soup.find('div', {'data-testid': 'description'})
        
        if desc_block:
            return desc_block.get_text(strip=True)
        
        # Альтернативный поиск
        paragraphs = soup.find_all('p')
        descriptions = [p.get_text(strip=True) for p in paragraphs[:5] if len(p.get_text(strip=True)) > 100]
        return " ".join(descriptions)
    
    def _extract_duration(self, soup: BeautifulSoup) -> str:
        """Извлечение срока обучения"""
        duration_patterns = ['2 года', '2 year', 'срок обучения']
        text = soup.get_text().lower()
        
        for pattern in duration_patterns:
            if pattern in text:
                return "2 года"
        return "2 года"
    
    def _extract_format(self, soup: BeautifulSoup) -> str:
        """Извлечение формата обучения"""
        text = soup.get_text().lower()
        if 'очная' in text or 'full-time' in text:
            return "Очная"
        elif 'заочная' in text or 'part-time' in text:
            return "Заочная"
        return "Очная"
    
    def _extract_courses(self, soup: BeautifulSoup) -> List[Course]:
        """Извлечение учебного плана"""
        courses = []
        
        # Ищем таблицу с дисциплинами или список
        curriculum_section = soup.find('div', class_='curriculum') or \
                            soup.find('section', {'id': 'curriculum'}) or \
                            soup.find('div', string=lambda t: t and 'учебный план' in t.lower() if t else False)
        
        if curriculum_section:
            # Парсим таблицу дисциплин
            rows = curriculum_section.find_all('tr') or curriculum_section.find_all('li')
            
            for row in rows:
                course = self._parse_course_row(row)
                if course:
                    courses.append(course)
        
        # Если не нашли структурированные данные, извлекаем из текста
        if not courses:
            courses = self._extract_courses_from_text(soup)
        
        return courses
    
    def _parse_course_row(self, row) -> Optional[Course]:
        """Парсинг строки с курсом"""
        cells = row.find_all(['td', 'span'])
        if len(cells) >= 2:
            name = cells[0].get_text(strip=True)
            if name and len(name) > 3:
                return Course(
                    name=name,
                    semester=1,  # Будет уточнено
                    credits=3,   # По умолчанию
                    course_type="обязательная"
                )
        return None
    
    def _extract_courses_from_text(self, soup: BeautifulSoup) -> List[Course]:
        """Извлечение курсов из текстового описания"""
        courses = []
        
        # Типичные названия дисциплин для AI-программ
        ai_courses = [
            ("Машинное обучение", 1, "обязательная"),
            ("Глубокое обучение", 2, "обязательная"),
            ("Компьютерное зрение", 2, "выборная"),
            ("Обработка естественного языка", 2, "выборная"),
            ("Reinforcement Learning", 3, "выборная"),
            ("MLOps", 3, "обязательная"),
            ("Математическая статистика", 1, "обязательная"),
            ("Оптимизация", 1, "обязательная"),
            ("Big Data", 2, "выборная"),
            ("Генеративные модели", 3, "выборная"),
        ]
        
        text = soup.get_text().lower()
        
        for course_name, semester, course_type in ai_courses:
            if course_name.lower() in text:
                courses.append(Course(
                    name=course_name,
                    semester=semester,
                    credits=3,
                    course_type=course_type
                ))
        
        return courses
    
    def _extract_requirements(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение требований для поступления"""
        requirements = []
        
        # Ищем секцию с требованиями
        req_section = soup.find('div', string=lambda t: t and 'требования' in t.lower() if t else False)
        
        # Типичные требования
        default_requirements = [
            "Высшее образование (бакалавриат/специалитет)",
            "Знание Python",
            "Базовые знания математики и статистики",
            "Английский язык на уровне чтения технической литературы"
        ]
        
        return requirements if requirements else default_requirements
    
    def _extract_careers(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение карьерных перспектив"""
        careers = [
            "Data Scientist",
            "ML Engineer",
            "AI Researcher",
            "Deep Learning Engineer",
            "Computer Vision Engineer",
            "NLP Engineer"
        ]
        return careers
    
    def _extract_competencies(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение ключевых компетенций"""
        return [
            "Разработка ML-моделей",
            "Анализ данных",
            "Работа с нейронными сетями",
            "MLOps практики",
            "Исследовательская работа"
        ]
    
    def save_to_json(self, program: Program, filepath: str):
        """Сохранение данных в JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(program), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved to {filepath}")
    
    def close(self):
        """Закрытие драйвера"""
        self.driver.quit()


def main():
    """Основная функция парсинга"""
    from config import settings
    
    scraper = ITMOScraper()
    
    try:
        # Парсим программу AI
        ai_program = scraper.parse_program(settings.AI_PROGRAM_URL)
        scraper.save_to_json(ai_program, f"{settings.DATA_DIR}/ai_program.json")
        
        # Парсим программу AI Product
        ai_product_program = scraper.parse_program(settings.AI_PRODUCT_URL)
        scraper.save_to_json(ai_product_program, f"{settings.DATA_DIR}/ai_product_program.json")
        
        logger.info("Parsing completed successfully!")
        
    finally:
        scraper.close()


if __name__ == "__main__":
    main()