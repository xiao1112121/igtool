import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class AIDataManager:
    """
    Quản lý dữ liệu AI accounts và chat groups
    - Load/Save AI accounts
    - Load/Save chat groups  
    - Backup và restore
    - Sync dữ liệu
    """
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.ai_accounts_file = os.path.join(base_dir, "ai_accounts.json")
        self.chat_groups_file = os.path.join(base_dir, "ai_chat_groups.json")
        self.backup_dir = os.path.join(base_dir, "data", "backups")
        
        # Tạo thư mục backup nếu chưa có
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Khởi tạo dữ liệu mặc định
        self.ai_accounts_data = self._load_ai_accounts()
        self.chat_groups_data = self._load_chat_groups()
        
        logger.info("AIDataManager initialized")
    
    def _load_ai_accounts(self) -> Dict[str, Any]:
        """Load dữ liệu AI accounts từ file"""
        try:
            if os.path.exists(self.ai_accounts_file):
                with open(self.ai_accounts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data.get('ai_accounts', []))} AI accounts")
                    return data
            else:
                # Tạo file mặc định
                default_data = {
                    "ai_accounts": [],
                    "groups": [],
                    "settings": {
                        "auto_save": True,
                        "backup_interval": 300,
                        "max_backups": 10,
                        "last_backup": datetime.now().isoformat()
                    }
                }
                self._save_ai_accounts(default_data)
                return default_data
        except Exception as e:
            logger.error(f"Error loading AI accounts: {e}")
            return {"ai_accounts": [], "groups": [], "settings": {}}
    
    def _load_chat_groups(self) -> Dict[str, Any]:
        """Load dữ liệu chat groups từ file"""
        try:
            if os.path.exists(self.chat_groups_file):
                with open(self.chat_groups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data.get('chat_groups', []))} chat groups")
                    return data
            else:
                # Tạo file mặc định
                default_data = {
                    "chat_groups": [],
                    "templates": {
                        "group_settings": {
                            "default_response_probability": 0.2,
                            "default_delay": {"min_seconds": 10, "max_seconds": 60},
                            "default_active_hours": {"start": "09:00", "end": "21:00"}
                        }
                    },
                    "metadata": {
                        "total_groups": 0,
                        "active_groups": 0,
                        "total_ai_accounts": 0,
                        "last_sync": datetime.now().isoformat(),
                        "version": "1.0.0"
                    }
                }
                self._save_chat_groups(default_data)
                return default_data
        except Exception as e:
            logger.error(f"Error loading chat groups: {e}")
            return {"chat_groups": [], "templates": {}, "metadata": {}}
    
    def _save_ai_accounts(self, data: Dict[str, Any]) -> bool:
        """Lưu dữ liệu AI accounts"""
        try:
            with open(self.ai_accounts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("AI accounts data saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving AI accounts: {e}")
            return False
    
    def _save_chat_groups(self, data: Dict[str, Any]) -> bool:
        """Lưu dữ liệu chat groups"""
        try:
            with open(self.chat_groups_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Chat groups data saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving chat groups: {e}")
            return False
    
    # === AI ACCOUNTS MANAGEMENT ===
    
    def get_ai_accounts(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả AI accounts"""
        return self.ai_accounts_data.get("ai_accounts", [])
    
    def add_ai_account(self, account_data: Dict[str, Any]) -> bool:
        """Thêm AI account mới"""
        try:
            # Tạo ID unique nếu chưa có
            if "id" not in account_data:
                account_data["id"] = f"ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Thêm timestamp
            account_data["created_date"] = datetime.now().isoformat()
            account_data["last_activity"] = datetime.now().isoformat()
            
            # Khởi tạo assigned_groups nếu chưa có
            if "assigned_groups" not in account_data:
                account_data["assigned_groups"] = []
            
            self.ai_accounts_data["ai_accounts"].append(account_data)
            self._save_ai_accounts(self.ai_accounts_data)
            
            logger.info(f"Added AI account: {account_data.get('telegram_username', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Error adding AI account: {e}")
            return False
    
    def update_ai_account(self, account_id: str, updates: Dict[str, Any]) -> bool:
        """Cập nhật AI account"""
        try:
            accounts = self.ai_accounts_data["ai_accounts"]
            for i, account in enumerate(accounts):
                if account.get("id") == account_id:
                    accounts[i].update(updates)
                    accounts[i]["last_activity"] = datetime.now().isoformat()
                    self._save_ai_accounts(self.ai_accounts_data)
                    logger.info(f"Updated AI account: {account_id}")
                    return True
            logger.warning(f"AI account not found: {account_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating AI account: {e}")
            return False
    
    def remove_ai_account(self, account_id: str) -> bool:
        """Xóa AI account"""
        try:
            accounts = self.ai_accounts_data["ai_accounts"]
            original_count = len(accounts)
            self.ai_accounts_data["ai_accounts"] = [acc for acc in accounts if acc.get("id") != account_id]
            
            if len(self.ai_accounts_data["ai_accounts"]) < original_count:
                self._save_ai_accounts(self.ai_accounts_data)
                logger.info(f"Removed AI account: {account_id}")
                return True
            else:
                logger.warning(f"AI account not found: {account_id}")
                return False
        except Exception as e:
            logger.error(f"Error removing AI account: {e}")
            return False
    
    # === CHAT GROUPS MANAGEMENT ===
    
    def get_chat_groups(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả chat groups"""
        return self.chat_groups_data.get("chat_groups", [])
    
    def add_chat_group(self, group_data: Dict[str, Any]) -> bool:
        """Thêm chat group mới"""
        try:
            # Tạo ID unique nếu chưa có
            if "id" not in group_data:
                group_data["id"] = f"group_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Thêm timestamp
            group_data["created_date"] = datetime.now().isoformat()
            group_data["last_updated"] = datetime.now().isoformat()
            
            # Khởi tạo assigned_ai_accounts nếu chưa có
            if "assigned_ai_accounts" not in group_data:
                group_data["assigned_ai_accounts"] = []
            
            # Khởi tạo statistics nếu chưa có
            if "statistics" not in group_data:
                group_data["statistics"] = {
                    "total_messages": 0,
                    "ai_messages": 0,
                    "ai_response_rate": 0.0,
                    "last_activity": datetime.now().isoformat(),
                    "peak_hours": []
                }
            
            self.chat_groups_data["chat_groups"].append(group_data)
            self._update_metadata()
            self._save_chat_groups(self.chat_groups_data)
            
            logger.info(f"Added chat group: {group_data.get('name', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Error adding chat group: {e}")
            return False
    
    def update_chat_group(self, group_id: str, updates: Dict[str, Any]) -> bool:
        """Cập nhật chat group"""
        try:
            groups = self.chat_groups_data["chat_groups"]
            for i, group in enumerate(groups):
                if group.get("id") == group_id:
                    groups[i].update(updates)
                    groups[i]["last_updated"] = datetime.now().isoformat()
                    self._update_metadata()
                    self._save_chat_groups(self.chat_groups_data)
                    logger.info(f"Updated chat group: {group_id}")
                    return True
            logger.warning(f"Chat group not found: {group_id}")
            return False
        except Exception as e:
            logger.error(f"Error updating chat group: {e}")
            return False
    
    def remove_chat_group(self, group_id: str) -> bool:
        """Xóa chat group"""
        try:
            groups = self.chat_groups_data["chat_groups"]
            original_count = len(groups)
            self.chat_groups_data["chat_groups"] = [grp for grp in groups if grp.get("id") != group_id]
            
            if len(self.chat_groups_data["chat_groups"]) < original_count:
                self._update_metadata()
                self._save_chat_groups(self.chat_groups_data)
                logger.info(f"Removed chat group: {group_id}")
                return True
            else:
                logger.warning(f"Chat group not found: {group_id}")
                return False
        except Exception as e:
            logger.error(f"Error removing chat group: {e}")
            return False
    
    # === RELATIONSHIP MANAGEMENT ===
    
    def assign_ai_to_group(self, ai_account_id: str, group_id: str) -> bool:
        """Gán AI account vào group"""
        try:
            # Tìm AI account
            ai_account = None
            for acc in self.ai_accounts_data["ai_accounts"]:
                if acc.get("id") == ai_account_id:
                    ai_account = acc
                    break
            
            if not ai_account:
                logger.error(f"AI account not found: {ai_account_id}")
                return False
            
            # Tìm group
            group = None
            for grp in self.chat_groups_data["chat_groups"]:
                if grp.get("id") == group_id:
                    group = grp
                    break
            
            if not group:
                logger.error(f"Chat group not found: {group_id}")
                return False
            
            # Thêm group vào AI account
            group_info = {
                "group_id": group_id,
                "group_name": group.get("name", ""),
                "group_link": group.get("invite_link", ""),
                "added_date": datetime.now().isoformat(),
                "role": "member"
            }
            
            if "assigned_groups" not in ai_account:
                ai_account["assigned_groups"] = []
            
            # Kiểm tra đã tồn tại chưa
            existing = any(g.get("group_id") == group_id for g in ai_account["assigned_groups"])
            if not existing:
                ai_account["assigned_groups"].append(group_info)
            
            # Thêm AI vào group
            ai_info = {
                "ai_account_id": ai_account_id,
                "telegram_phone": ai_account.get("telegram_phone", ""),
                "telegram_username": ai_account.get("telegram_username", ""),
                "personality": ai_account.get("ai_personality", ""),
                "role": "member",
                "join_date": datetime.now().isoformat(),
                "last_message": None,
                "message_count": 0,
                "status": "active"
            }
            
            if "assigned_ai_accounts" not in group:
                group["assigned_ai_accounts"] = []
            
            # Kiểm tra đã tồn tại chưa
            existing = any(ai.get("ai_account_id") == ai_account_id for ai in group["assigned_ai_accounts"])
            if not existing:
                group["assigned_ai_accounts"].append(ai_info)
            
            # Lưu cả hai file
            self._save_ai_accounts(self.ai_accounts_data)
            self._save_chat_groups(self.chat_groups_data)
            
            logger.info(f"Assigned AI {ai_account_id} to group {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning AI to group: {e}")
            return False
    
    def unassign_ai_from_group(self, ai_account_id: str, group_id: str) -> bool:
        """Bỏ gán AI account khỏi group"""
        try:
            # Xóa group khỏi AI account
            for acc in self.ai_accounts_data["ai_accounts"]:
                if acc.get("id") == ai_account_id:
                    if "assigned_groups" in acc:
                        acc["assigned_groups"] = [g for g in acc["assigned_groups"] if g.get("group_id") != group_id]
                    break
            
            # Xóa AI khỏi group
            for grp in self.chat_groups_data["chat_groups"]:
                if grp.get("id") == group_id:
                    if "assigned_ai_accounts" in grp:
                        grp["assigned_ai_accounts"] = [ai for ai in grp["assigned_ai_accounts"] if ai.get("ai_account_id") != ai_account_id]
                    break
            
            # Lưu cả hai file
            self._save_ai_accounts(self.ai_accounts_data)
            self._save_chat_groups(self.chat_groups_data)
            
            logger.info(f"Unassigned AI {ai_account_id} from group {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unassigning AI from group: {e}")
            return False
    
    # === BACKUP & RESTORE ===
    
    def create_backup(self) -> str:
        """Tạo backup của tất cả dữ liệu AI"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"ai_backup_{timestamp}.json"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "ai_accounts": self.ai_accounts_data,
                "chat_groups": self.chat_groups_data,
                "version": "1.0.0"
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            logger.info(f"Backup created: {backup_filename}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return ""
    
    def restore_backup(self, backup_path: str) -> bool:
        """Khôi phục từ backup"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Restore data
            if "ai_accounts" in backup_data:
                self.ai_accounts_data = backup_data["ai_accounts"]
                self._save_ai_accounts(self.ai_accounts_data)
            
            if "chat_groups" in backup_data:
                self.chat_groups_data = backup_data["chat_groups"]
                self._save_chat_groups(self.chat_groups_data)
            
            logger.info(f"Restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Xóa backup cũ (chỉ giữ lại 10 file mới nhất)"""
        try:
            backup_files = [f for f in os.listdir(self.backup_dir) if f.startswith("ai_backup_") and f.endswith(".json")]
            backup_files.sort(reverse=True)  # Mới nhất trước
            
            max_backups = self.ai_accounts_data.get("settings", {}).get("max_backups", 10)
            
            for old_backup in backup_files[max_backups:]:
                old_path = os.path.join(self.backup_dir, old_backup)
                os.remove(old_path)
                logger.info(f"Removed old backup: {old_backup}")
                
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
    
    def _update_metadata(self):
        """Cập nhật metadata cho chat groups"""
        try:
            groups = self.chat_groups_data.get("chat_groups", [])
            total_groups = len(groups)
            active_groups = len([g for g in groups if g.get("status") == "active"])
            
            # Đếm tổng AI accounts được assign
            total_ai_accounts = 0
            for group in groups:
                total_ai_accounts += len(group.get("assigned_ai_accounts", []))
            
            self.chat_groups_data["metadata"] = {
                "total_groups": total_groups,
                "active_groups": active_groups,
                "total_ai_accounts": total_ai_accounts,
                "last_sync": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
    
    # === UTILITY METHODS ===
    
    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê tổng quan"""
        try:
            ai_accounts = self.get_ai_accounts()
            chat_groups = self.get_chat_groups()
            
            stats = {
                "ai_accounts": {
                    "total": len(ai_accounts),
                    "active": len([acc for acc in ai_accounts if acc.get("status") == "active"]),
                    "personalities": {}
                },
                "chat_groups": {
                    "total": len(chat_groups),
                    "active": len([grp for grp in chat_groups if grp.get("status") == "active"]),
                    "total_members": sum(grp.get("member_count", 0) for grp in chat_groups)
                },
                "assignments": {
                    "total_assignments": 0,
                    "active_assignments": 0
                }
            }
            
            # Thống kê personalities
            for acc in ai_accounts:
                personality = acc.get("ai_personality", "unknown")
                stats["ai_accounts"]["personalities"][personality] = stats["ai_accounts"]["personalities"].get(personality, 0) + 1
            
            # Thống kê assignments
            for acc in ai_accounts:
                assigned_groups = acc.get("assigned_groups", [])
                stats["assignments"]["total_assignments"] += len(assigned_groups)
                stats["assignments"]["active_assignments"] += len([g for g in assigned_groups if g.get("status", "active") == "active"])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def sync_data(self) -> bool:
        """Đồng bộ dữ liệu và tạo backup tự động"""
        try:
            # Tạo backup tự động
            self.create_backup()
            
            # Cập nhật timestamp
            self.ai_accounts_data.setdefault("settings", {})["last_backup"] = datetime.now().isoformat()
            self._save_ai_accounts(self.ai_accounts_data)
            
            self._update_metadata()
            self._save_chat_groups(self.chat_groups_data)
            
            logger.info("Data synced successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing data: {e}")
            return False 