
import requests
import json
import logging
from typing import Optional, Dict, List, Any

# =================================================================================
# 配置区域
# =================================================================================
# API 基础地址
API_BASE_URL = "http://127.0.0.1:8000/api/v1/exchange/emails"
# 生产环境示例: 
# API_BASE_URL = "https://10.78.4.119:9998/api/v1/exchange/emails"

# API Key (请替换为实际申请的 Key)
API_KEY = "9e55f7ee4fc9eb133df840381a9bd05d6c8fe69ec4b032ecb03e08e8ce78b389"

# 目标邮箱 Account ID (请替换为实际的 Account ID)
ACCOUNT_ID = 5

# =================================================================================
# 日志配置
# =================================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EmailApiClient:
    """
    邮件服务 API 客户端示例
    """
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Content-Type": "application/json",
            "X-Api-Key": api_key  # 关键：通过 X-Api-Key 头传递认证信息
        }

    def list_emails(self, account_id: int, folder: str = "INBOX", limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        获取邮件列表
        """
        url = f"{self.base_url}/list"
        params = {
            "account_id": account_id,
            "folder": folder,
            "limit": limit,
            "offset": offset,
            "unread_only": False
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                data = result.get("data", {})
                logger.info(f"获取邮件列表成功: 总数 {data.get('total')}, 本次获取 {len(data.get('items', []))}")
                return data.get("items", [])
            else:
                logger.error(f"API 业务错误: {result}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP 请求失败: {e}")
            return []

    def get_email_details(self, email_id: str, account_id: int) -> Optional[Dict]:
        """
        获取邮件详情
        """
        # 注意: email_id 可能会包含特殊字符，requests 会自动处理 URL 编码
        # 但如果是手动拼接 URL，请务必使用 quote(email_id) 进行编码
        url = f"{self.base_url}/{email_id}" 
        params = {
            "account_id": account_id
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                logger.info("获取邮件详情成功")
                return result.get("data")
            else:
                logger.error(f"API 业务错误: {result}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP 请求失败: {e}")
            return None

    def mark_as_read(self, email_id: str, account_id: int) -> bool:
        """
        标记邮件为已读
        """
        url = f"{self.base_url}/{email_id}/read"
        params = {
            "account_id": account_id,
            "is_read": True
        }
        
        try:
            response = requests.put(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                logger.info(f"标记邮件已读成功: {result.get('msg')}")
                return True
            else:
                logger.error(f"API 业务错误: {result}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP 请求失败: {e}")
            return False

    def sync_emails(self, account_id: int, sync_state: Optional[str] = None) -> Dict[str, Any]:
        """
        增量同步邮件
        
        Args:
            sync_state: 上次同步返回的 state 字符串。如果是第一次同步，传 None。
            
        Returns:
            Dict: 包含 'sync_state' (新状态) 和 'items' (变更列表)
        """
        url = f"{self.base_url}/sync"
        payload = {
            "account_id": account_id,
            "limit": 50,
            "folder": "INBOX",
            "sync_state": sync_state
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 200:
                data = result.get("data", {})
                new_state = data.get("sync_state")
                changes = data.get("items", [])
                
                logger.info(f"同步成功. 变更数: {len(changes)}")
                return {
                    "sync_state": new_state,
                    "items": changes
                }
            else:
                logger.error(f"API 业务错误: {result}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP 请求失败: {e}")
            return {}


def main():
    """
    Api Usage Demo
    """
    client = EmailApiClient(base_url=API_BASE_URL, api_key=API_KEY)
    
    # 1. 列出邮件
    print("\n--- 1. List Emails ---")
    emails = client.list_emails(account_id=ACCOUNT_ID, limit=5)
    
    if not emails:
        print("未获取到邮件，结束演示")
        return

    first_email = emails[0]
    email_id = first_email['id']
    print(f"Latest Email: {first_email.get('subject')} (ID: {email_id[:20]}...)")
    
    # 2. 获取详情
    print("\n--- 2. Get Details ---")
    details = client.get_email_details(email_id=email_id, account_id=ACCOUNT_ID)
    if details:
        print(f"Body Preview: {details.get('body', '')[:50]}...")
        if details.get('attachments'):
            print(f"Attachments: {[att['name'] for att in details['attachments']]}")
    
    # 3. 标记已读
    print("\n--- 3. Mark Read ---")
    client.mark_as_read(email_id=email_id, account_id=ACCOUNT_ID)
    
    # 4. 增量同步
    print("\n--- 4. Sync Emails ---")
    # 第一次同步，sync_state 为 None
    sync_result = client.sync_emails(account_id=ACCOUNT_ID, sync_state=None)
    
    new_state = sync_result.get("sync_state")
    print(f"Initial Sync state: {new_state[:50]}...")
    
    # 模拟第二次同步 (使用上次的 state)
    if new_state:
        print("\n--- 4.1 Sync Again (No changes expected) ---")
        client.sync_emails(account_id=ACCOUNT_ID, sync_state=new_state)

if __name__ == "__main__":
    main()
