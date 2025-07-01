import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.types import User, Chat, Channel
import random
import time
from .ai_client import get_ai_client

logger = logging.getLogger(__name__)

class TelegramAIBot:
    def __init__(self, phone: str, session_path: str, proxy: Optional[Dict] = None):
        """Initialize Telegram AI Bot for a specific account"""
        self.phone = phone
        self.session_path = session_path
        self.proxy = proxy
        self.client = None
        self.is_connected = False
        self.user_info = None
        self.ai_client = get_ai_client()
        
        # Bot settings
        self.personality = "Thân thiện"
        self.response_frequency = 5  # 1-10 scale
        self.response_speed = (3, 20)  # seconds range
        self.enthusiasm_level = 5  # 1-10 scale
        self.emotion = "Positive"  # Positive, Neutral, Negative, Random
        self.keywords = []
        
        # Activity tracking
        self.messages_sent = 0
        self.last_activity = None
        self.status = "Idle"
        
        logger.info(f"Initialized TelegramAIBot for {phone}")
    
    async def connect(self, api_id: int, api_hash: str) -> bool:
        """Connect to Telegram using existing session"""
        try:
            # Setup proxy if available
            proxy_config = None
            if self.proxy:
                proxy_parts = self.proxy.split(':')
                if len(proxy_parts) >= 4:
                    proxy_config = {
                        'proxy_type': 'http',
                        'addr': proxy_parts[0],
                        'port': int(proxy_parts[1]),
                        'username': proxy_parts[2],
                        'password': proxy_parts[3]
                    }
            
            # Create client
            self.client = TelegramClient(
                self.session_path,
                api_id,
                api_hash,
                proxy=proxy_config
            )
            
            # Connect and get user info
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                self.user_info = await self.client.get_me()
                self.is_connected = True
                self.status = "Online"
                logger.info(f"Successfully connected bot for {self.phone} - {self.user_info.first_name}")
                return True
            else:
                logger.error(f"Session not authorized for {self.phone}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect bot for {self.phone}: {e}")
            self.status = "Error"
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            self.status = "Offline"
            logger.info(f"Disconnected bot for {self.phone}")
    
    async def send_ai_message(self, chat_id: str, trigger_message: str = "", context: str = "") -> Dict[str, Any]:
        """Generate and send AI message to a chat"""
        if not self.is_connected or not self.client:
            return {"success": False, "error": "Bot not connected"}
        
        try:
            self.status = "Processing"
            
            # Check if should respond based on frequency
            if not self.should_respond():
                return {"success": False, "error": "Skipped based on response frequency"}
            
            # Generate AI response
            ai_result = await self.ai_client.generate_response(
                message=trigger_message or "Hãy nói một câu thú vị",
                personality=self.personality,
                context=context
            )
            
            if not ai_result["success"]:
                self.status = "Error"
                return ai_result
            
            # Add natural delay
            delay = self.calculate_response_delay()
            await asyncio.sleep(delay)
            
            # Send message
            await self.client.send_message(chat_id, ai_result["response"])
            
            # Update activity
            self.messages_sent += 1
            self.last_activity = time.time()
            self.status = "Active"
            
            logger.info(f"Bot {self.phone} sent message to {chat_id}: {ai_result['response'][:50]}...")
            
            return {
                "success": True,
                "message": ai_result["response"],
                "delay_used": delay,
                "tokens_used": ai_result.get("tokens_used", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to send AI message from {self.phone}: {e}")
            self.status = "Error"
            return {"success": False, "error": str(e)}
    
    def should_respond(self) -> bool:
        """Determine if bot should respond based on frequency setting"""
        # Convert frequency (1-10) to probability (10%-100%)
        probability = self.response_frequency * 10
        return random.randint(1, 100) <= probability
    
    def calculate_response_delay(self) -> float:
        """Calculate natural response delay based on settings"""
        min_delay, max_delay = self.response_speed
        
        # Adjust based on enthusiasm level
        enthusiasm_factor = (11 - self.enthusiasm_level) / 10  # Higher enthusiasm = faster response
        
        base_delay = random.uniform(min_delay, max_delay)
        adjusted_delay = base_delay * enthusiasm_factor
        
        return max(1.0, adjusted_delay)  # Minimum 1 second delay
    
    def update_personality(self, personality: str, frequency: int = 5, speed: tuple = (3, 20), 
                          enthusiasm: int = 5, emotion: str = "Positive", keywords: List[str] = None):
        """Update bot personality and behavior settings"""
        self.personality = personality
        self.response_frequency = max(1, min(10, frequency))
        self.response_speed = speed
        self.enthusiasm_level = max(1, min(10, enthusiasm))
        self.emotion = emotion
        self.keywords = keywords or []
        
        logger.info(f"Updated personality for {self.phone}: {personality}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status and statistics"""
        return {
            "phone": self.phone,
            "status": self.status,
            "is_connected": self.is_connected,
            "personality": self.personality,
            "messages_sent": self.messages_sent,
            "last_activity": self.last_activity,
            "user_info": {
                "first_name": self.user_info.first_name if self.user_info else "",
                "username": self.user_info.username if self.user_info else "",
                "id": self.user_info.id if self.user_info else ""
            } if self.user_info else None
        }

class TelegramBotManager:
    def __init__(self, telegram_config_path: str = "telegram_config.json"):
        """Initialize Telegram Bot Manager"""
        self.telegram_config = self.load_telegram_config(telegram_config_path)
        self.api_id = self.telegram_config["api_id"]
        self.api_hash = self.telegram_config["api_hash"]
        
        self.bots: Dict[str, TelegramAIBot] = {}
        self.active_groups: Dict[str, List[str]] = {}  # group_id -> list of bot phones
        
        logger.info("TelegramBotManager initialized")
    
    def load_telegram_config(self, config_path: str) -> Dict:
        """Load Telegram API configuration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Telegram config: {e}")
            raise
    
    async def add_bot(self, phone: str, session_path: str, proxy: Optional[str] = None) -> bool:
        """Add and connect a new AI bot"""
        try:
            # Parse proxy if provided
            proxy_dict = None
            if proxy:
                proxy_dict = proxy
            
            # Create bot instance
            bot = TelegramAIBot(phone, session_path, proxy_dict)
            
            # Connect to Telegram
            if await bot.connect(self.api_id, self.api_hash):
                self.bots[phone] = bot
                logger.info(f"Successfully added bot: {phone}")
                return True
            else:
                logger.error(f"Failed to connect bot: {phone}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding bot {phone}: {e}")
            return False
    
    async def remove_bot(self, phone: str) -> bool:
        """Remove and disconnect a bot"""
        if phone in self.bots:
            await self.bots[phone].disconnect()
            del self.bots[phone]
            logger.info(f"Removed bot: {phone}")
            return True
        return False
    
    async def assign_bots_to_group(self, group_id: str, bot_phones: List[str]):
        """Assign bots to monitor and respond in a group"""
        self.active_groups[group_id] = bot_phones
        logger.info(f"Assigned {len(bot_phones)} bots to group {group_id}")
    
    async def send_group_messages(self, group_id: str, trigger_message: str = "", context: str = "") -> Dict[str, Any]:
        """Send AI messages from all assigned bots to a group"""
        if group_id not in self.active_groups:
            return {"success": False, "error": "No bots assigned to this group"}
        
        results = []
        bot_phones = self.active_groups[group_id]
        
        for phone in bot_phones:
            if phone in self.bots:
                bot = self.bots[phone]
                result = await bot.send_ai_message(group_id, trigger_message, context)
                results.append({
                    "phone": phone,
                    "result": result
                })
                
                # Add delay between bots to avoid spam detection
                await asyncio.sleep(random.uniform(1, 3))
        
        success_count = sum(1 for r in results if r["result"]["success"])
        
        return {
            "success": True,
            "group_id": group_id,
            "total_bots": len(bot_phones),
            "successful_sends": success_count,
            "results": results
        }
    
    def update_bot_personality(self, phone: str, **kwargs):
        """Update personality settings for a specific bot"""
        if phone in self.bots:
            self.bots[phone].update_personality(**kwargs)
            return True
        return False
    
    def get_all_bot_status(self) -> List[Dict[str, Any]]:
        """Get status of all bots"""
        return [bot.get_status() for bot in self.bots.values()]
    
    def get_active_bots_count(self) -> int:
        """Get count of active/connected bots"""
        return sum(1 for bot in self.bots.values() if bot.is_connected)
    
    async def emergency_stop_all(self):
        """Emergency stop all bot activities"""
        for bot in self.bots.values():
            bot.status = "Stopped"
        logger.warning("Emergency stop activated for all bots")
    
    async def shutdown_all(self):
        """Disconnect all bots"""
        for phone in list(self.bots.keys()):
            await self.remove_bot(phone)
        logger.info("All bots disconnected")

# Global bot manager instance
bot_manager = None

def get_bot_manager() -> TelegramBotManager:
    """Get global bot manager instance"""
    global bot_manager
    if bot_manager is None:
        bot_manager = TelegramBotManager()
    return bot_manager

def initialize_bot_manager(config_path: str = "telegram_config.json") -> TelegramBotManager:
    """Initialize global bot manager"""
    global bot_manager
    bot_manager = TelegramBotManager(config_path)
    return bot_manager
