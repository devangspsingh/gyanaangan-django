import json
import requests
import logging
from django.conf import settings
from .models import LLMProviderConfig, Topic, PYQTopicMap

logger = logging.getLogger(__name__)

class LLMService:
    @staticmethod
    def get_active_config():
        return LLMProviderConfig.objects.filter(is_active=True).first()

    @staticmethod
    def call_llm(system_prompt: str, user_prompt: str) -> dict:
        config = LLMService.get_active_config()
        if not config:
            raise ValueError("No active LLM Provider configured in the admin panel.")

        url = ""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        if config.provider == 'groq':
            url = "https://api.groq.com/openai/v1/chat/completions"
        elif config.provider == 'openrouter':
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers["HTTP-Referer"] = getattr(settings, 'SITE_URL', 'http://localhost:8000') 
            headers["X-Title"] = "GyanAangan"

        payload = {
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"}, 
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM API Call failed: {e}")
            return {}

    @classmethod
    def process_syllabus(cls, subject):
        """Processes the syllabus_text of a subject into Topic objects."""
        if not subject.syllabus_text:
            return []
            
        system = (
            "You are an academic assistant. Extract a clean list of topics from the given syllabus. "
            "Rules:\n- Keep topic names short and standard\n- Avoid duplicates\n- Split into meaningful units\n"
            "Return JSON explicitly in this format: { \"topics\": [{\"topic\": \"Topic 1\"}, {\"topic\": \"Topic 2\"}] }"
        )
        
        data = cls.call_llm(system, subject.syllabus_text)
        extracted = data.get("topics", [])
        
        new_topics = []
        for item in extracted:
            topic_name = item.get("topic")
            if topic_name:
                obj, created = Topic.objects.get_or_create(
                    subject=subject, 
                    name=topic_name.strip()
                )
                new_topics.append(obj)
                
        return new_topics

    @classmethod
    def extract_pyq_topics(cls, resource, question_text):
        """Processes PYQ questions to map them to topics."""
        if not question_text:
            return None

        system = (
            "You are given a previous year exam question from an academic paper. "
            "Identify:\n1. The main topic\n2. Question type (short/long)\n3. Importance weight (1-10)\n"
            "Return JSON strictly in this format: { \"topic\": \"Process Scheduling\", \"type\": \"short|long\", \"weight\": 9 }"
        )
        
        data = cls.call_llm(system, question_text)
        
        topic_name = data.get("topic")
        q_type = data.get("type", "short").lower()
        weight = int(data.get("weight", 5))
        
        if q_type not in ['short', 'long']:
            q_type = 'short'
        
        if topic_name:
            # We assume syllabus is processed first, so topic exists. Otherwise create it.
            topic, _ = Topic.objects.get_or_create(
                subject=resource.subject,
                name=topic_name.strip()
            )
            
            mapping = PYQTopicMap.objects.create(
                resource=resource,
                topic=topic,
                question_text=question_text,
                marks_type=q_type,
                weight=weight
            )
            
            # Recalculate properties for Priority Logic dynamically
            topic.pyq_frequency += 1
            topic.marks_weight += weight
            topic.save()
            
            return mapping
        return None
