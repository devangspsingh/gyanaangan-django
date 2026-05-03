import json
import logging
from django.conf import settings
from groq import Groq
from openai import OpenAI
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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        print("\n" + "="*50)
        print(f"🤖 LLM API REQUEST to {config.provider.upper()}")
        print(f"System Prompt: {system_prompt}")
        print(f"User Prompt: {user_prompt[:500]}..." if len(user_prompt) > 500 else f"User Prompt: {user_prompt}")
        print("="*50 + "\n")
        
        try:
            content = ""
            if config.provider == 'groq':
                client = Groq(api_key=config.api_key)
                response = client.chat.completions.create(
                    model=config.model_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                content = response.choices[0].message.content

            elif config.provider == 'openrouter':
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=config.api_key,
                )
                response = client.chat.completions.create(
                    model=config.model_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    extra_headers={
                        "HTTP-Referer": getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                        "X-Title": "GyanAangan",
                    }
                )
                content = response.choices[0].message.content

            print("\n" + "="*50)
            print("🟢 LLM API RESPONSE")
            print(content)
            print("="*50 + "\n")

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
        """Processes an entire PYQ paper to extract multiple questions and map them to topics."""
        if not question_text:
            return []

        # Get existing topics
        existing_topics = list(Topic.objects.filter(subject=resource.subject).values_list('name', flat=True))
        topics_list_str = ", ".join(existing_topics) if existing_topics else "None"

        system = (
            "You are given a document containing a Previous Year Question (PYQ) paper. "
            "Extract EACH individual question. For each question, identify:\n"
            "1. The main topics (can be multiple, short specific names). Mappings to existing topics are preferred if relevant:\n"
            f"   [Existing Topics: {topics_list_str}]\n"
            "2. Question type ('short' or 'long')\n"
            "3. Importance weight (1-10)\n"
            "Return JSON strictly in this format: "
            "{ \"questions\": [{\"topics\": [\"Cloud Architecture\", \"Virtualization\"], \"type\": \"long\", \"weight\": 8, \"question_text\": \"Describe the Cloud Computing Architecture.\"}, ...] }"
        )
        
        data = cls.call_llm(system, question_text)
        extracted = data.get("questions", [])
        
        mappings = []
        for item in extracted:
            topics_list = item.get("topics", [])
            # Fallback if model answered with 'topic'
            if not topics_list and "topic" in item:
                val = item.get("topic")
                if isinstance(val, list):
                    topics_list = val
                else:
                    topics_list = [val]
                    
            q_type = item.get("type", "short").lower()
            try:
                weight = int(item.get("weight", 5))
            except ValueError:
                weight = 5
            q_text = item.get("question_text", "")
            
            if q_type not in ['short', 'long']:
                q_type = 'short'
            
            for topic_name in topics_list:
                if topic_name:
                    topic, _ = Topic.objects.get_or_create(
                        subject=resource.subject,
                        name=topic_name.strip()
                    )
                    
                    mapping = PYQTopicMap.objects.create(
                        resource=resource,
                        topic=topic,
                        question_text=q_text,
                        marks_type=q_type,
                        weight=weight
                    )
                    
                    # Recalculate properties dynamically
                    topic.pyq_frequency += 1
                    topic.marks_weight += weight
                    topic.save()
                    
                    mappings.append(mapping)
                
        return mappings
