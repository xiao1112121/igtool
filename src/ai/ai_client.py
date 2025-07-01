import json
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import time
import random

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self, config_path: str = "ai_config.json"):
        """Initialize AI client with Groq API configuration"""
        self.config = self.load_config(config_path)
        self.api_key = self.config["api_key"]
        self.base_url = self.config["base_url"]
        self.default_model = self.config["default_model"]
        self.max_tokens = self.config.get("max_tokens", 150)
        self.temperature = self.config.get("temperature", 0.7)
        
        # Rate limiting
        self.rate_limits = self.config.get("rate_limits", {})
        self.requests_per_minute = self.rate_limits.get("requests_per_minute", 30)
        self.last_request_times = []
        
        logger.info(f"AI Client initialized with Groq API - Model: {self.default_model}")
    
    def load_config(self, config_path: str) -> Dict:
        """Load AI configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Loaded AI config from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"AI config file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise
    
    def check_rate_limit(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        now = time.time()
        # Remove requests older than 1 minute
        self.last_request_times = [t for t in self.last_request_times if now - t < 60]
        
        if len(self.last_request_times) >= self.requests_per_minute:
            return False
        return True
    
    def add_request_time(self):
        """Record the time of a request"""
        self.last_request_times.append(time.time())
    
    async def generate_response(
        self, 
        message: str, 
        personality: str = "Thân thiện",
        context: str = "",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AI response using Groq API"""
        
        if not self.check_rate_limit():
            wait_time = 60 - (time.time() - min(self.last_request_times))
            logger.warning(f"Rate limit hit, waiting {wait_time:.1f} seconds")
            await asyncio.sleep(wait_time)
        
        try:
            # Build system prompt based on personality
            system_prompt = self.build_system_prompt(personality, context)
            
            # Prepare request payload
            payload = {
                "model": model or self.default_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    self.add_request_time()
                    
                    if response.status == 200:
                        data = await response.json()
                        ai_response = data["choices"][0]["message"]["content"]
                        
                        # Add random delay for natural behavior
                        delay = random.uniform(2, 8)
                        
                        return {
                            "success": True,
                            "response": ai_response.strip(),
                            "delay": delay,
                            "model_used": payload["model"],
                            "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API Error {response.status}: {error_text}",
                            "delay": 0
                        }
                        
        except asyncio.TimeoutError:
            logger.error("API request timeout")
            return {
                "success": False,
                "error": "Request timeout",
                "delay": 0
            }
        except Exception as e:
            logger.error(f"Unexpected error in AI generation: {e}")
            return {
                "success": False,
                "error": str(e),
                "delay": 0
            }
    
    def build_system_prompt(self, personality: str, context: str = "") -> str:
        """Build system prompt based on personality and context"""
        
        personality_prompts = {
            "Hài hước": "Bạn là một người rất hài hước, thích đùa cợt và tạo không khí vui vẻ. Trả lời một cách tự nhiên và hài hước.",
            "Nghiêm túc": "Bạn là một người nghiêm túc, chuyên nghiệp. Trả lời một cách trang trọng và có tính học thuật.",
            "Thân thiện": "Bạn là một người thân thiện, gần gũi và dễ mến. Trả lời một cách ấm áp và chân thành.",
            "Tò mò": "Bạn là một người rất tò mò, thích khám phá và đặt câu hỏi. Trả lời với sự háo hức và tò mò.",
            "Lạc quan": "Bạn là một người lạc quan, tích cực và luôn nhìn về mặt tích cực của mọi việc.",
            "Trí thức": "Bạn là một người có học thức, thích chia sẻ kiến thức và thông tin hữu ích.",
            "Sáng tạo": "Bạn là một người sáng tạo, thích nghĩ ra những ý tưởng mới và độc đáo.",
            "Bình tĩnh": "Bạn là một người bình tĩnh, điềm đạm và luôn giữ được sự tĩnh lặng.",
            "Nhiệt tình": "Bạn là một người nhiệt tình, năng động và đầy năng lượng.",
            "Giản dị": "Bạn là một người giản dị, chân phương và không thích phô trương.",
            "Thông minh": "Bạn là một người thông minh, nhanh trí và có khả năng phân tích tốt.",
            "Ấm áp": "Bạn là một người ấm áp, quan tâm và luôn lắng nghe người khác."
        }
        
        base_prompt = personality_prompts.get(personality, personality_prompts["Thân thiện"])
        
        system_prompt = f"{base_prompt} Trả lời bằng tiếng Việt, ngắn gọn (1-2 câu), tự nhiên như đang chat với bạn bè."
        
        if context:
            system_prompt += f" Ngữ cảnh cuộc trò chuyện: {context}"
        
        return system_prompt
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return self.config.get("models", [self.default_model])
    
    def update_config(self, new_config: Dict):
        """Update AI configuration"""
        self.config.update(new_config)
        self.api_key = self.config["api_key"]
        self.base_url = self.config["base_url"]
        self.default_model = self.config["default_model"]
        self.max_tokens = self.config.get("max_tokens", 150)
        self.temperature = self.config.get("temperature", 0.7)
        logger.info("AI configuration updated")

# Global AI client instance
ai_client = None

def get_ai_client() -> AIClient:
    """Get global AI client instance"""
    global ai_client
    if ai_client is None:
        ai_client = AIClient()
    return ai_client

def initialize_ai_client(config_path: str = "ai_config.json") -> AIClient:
    """Initialize global AI client"""
    global ai_client
    ai_client = AIClient(config_path)
    return ai_client 