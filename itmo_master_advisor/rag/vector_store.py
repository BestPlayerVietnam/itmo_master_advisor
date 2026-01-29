"""
Векторное хранилище для RAG
"""
import json
from typing import List, Dict
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import logging

from config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Векторное хранилище на базе ChromaDB"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="itmo_programs",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def load_and_index_programs(self):
        """Загрузка и индексация программ"""
        programs_data = []
        
        # Загружаем данные программ
        for filename in ["ai_program.json", "ai_product_program.json"]:
            filepath = f"{settings.DATA_DIR}/{filename}"
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    programs_data.append(data)
            except FileNotFoundError:
                logger.warning(f"File not found: {filepath}")
        
        # Подготавливаем документы для индексации
        documents = []
        metadatas = []
        ids = []
        
        for idx, program in enumerate(programs_data):
            # Основная информация о программе
            program_text = self._format_program_text(program)
            chunks = self.text_splitter.split_text(program_text)
            
            for chunk_idx, chunk in enumerate(chunks):
                doc_id = f"{program['name']}_{chunk_idx}"
                documents.append(chunk)
                metadatas.append({
                    "program": program['name'],
                    "url": program['url'],
                    "type": "general"
                })
                ids.append(doc_id)
            
            # Информация о курсах
            for course in program.get('courses', []):
                course_text = self._format_course_text(course, program['name'])
                doc_id = f"{program['name']}_course_{course['name']}"
                documents.append(course_text)
                metadatas.append({
                    "program": program['name'],
                    "course": course['name'],
                    "type": "course",
                    "course_type": course.get('course_type', 'unknown')
                })
                ids.append(doc_id)
        
        # Получаем эмбеддинги
        if documents:
            embeddings = self.embeddings.embed_documents(documents)
            
            # Добавляем в коллекцию
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Indexed {len(documents)} documents")
    
    def _format_program_text(self, program: Dict) -> str:
        """Форматирование информации о программе"""
        text = f"""
        Программа: {program['name']}
        URL: {program['url']}
        
        Описание: {program.get('description', 'Нет описания')}
        
        Срок обучения: {program.get('duration', '2 года')}
        Формат: {program.get('format', 'Очная')}
        
        Требования для поступления:
        {chr(10).join('- ' + req for req in program.get('admission_requirements', []))}
        
        Карьерные перспективы:
        {chr(10).join('- ' + career for career in program.get('career_prospects', []))}
        
        Ключевые компетенции:
        {chr(10).join('- ' + comp for comp in program.get('key_competencies', []))}
        """
        return text.strip()
    
    def _format_course_text(self, course: Dict, program_name: str) -> str:
        """Форматирование информации о курсе"""
        text = f"""
        Программа: {program_name}
        Курс: {course['name']}
        Семестр: {course.get('semester', 'Не указан')}
        Кредиты: {course.get('credits', 'Не указаны')}
        Тип: {course.get('course_type', 'Не указан')}
        Описание: {course.get('description', 'Нет описания')}
        """
        return text.strip()
    
    def search(self, query: str, top_k: int = None, filter_dict: Dict = None) -> List[Dict]:
        """Поиск релевантных документов"""
        top_k = top_k or settings.TOP_K_RESULTS
        
        query_embedding = self.embeddings.embed_query(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )
        
        documents = []
        for i in range(len(results['documents'][0])):
            documents.append({
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results else None
            })
        
        return documents
    
    def clear(self):
        """Очистка коллекции"""
        self.client.delete_collection("itmo_programs")
        self.collection = self.client.create_collection(
            name="itmo_programs",
            metadata={"hnsw:space": "cosine"}
        )