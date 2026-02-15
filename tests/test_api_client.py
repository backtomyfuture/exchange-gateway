"""
Exchange 邮件网关 API 测试客户端
测试所有 API 端点功能
"""
import requests
import json
from datetime import datetime, timedelta

# =========================================================================
# 配置
# =========================================================================
API_BASE_URL = "http://10.78.4.119:9998/api/v1/exchange"
# 请替换为您创建的真实 API Key
API_KEY = "57e52c04420e41f27e7ac02aef011709d270622490824754addcb0b815cf9a77"
# 请替换为您要操作的 Exchange 账户 ID (在管理后台查看)
ACCOUNT_ID = 1
# 测试邮件收件人
TEST_RECIPIENT = "q-fu@tianjin-air.com"

# 公共请求头
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}


def print_response(response, title):
    """打印响应结果"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except Exception:
        print(response.text)
        return None


def print_section(title):
    """打印分节标题"""
    print(f"\n\n{'#'*70}")
    print(f"# {title}")
    print(f"{'#'*70}")


# =========================================================================
# 邮件操作测试
# =========================================================================

def test_list_folders():
    """测试：获取文件夹列表"""
    url = f"{API_BASE_URL}/emails/folders/list"
    params = {"account_id": ACCOUNT_ID}
    
    response = requests.get(url, headers=HEADERS, params=params)
    return print_response(response, "获取文件夹列表")


def test_list_emails(folder="INBOX", limit=5):
    """测试：获取邮件列表"""
    url = f"{API_BASE_URL}/emails/list"
    params = {
        "account_id": ACCOUNT_ID,
        "folder": folder,
        "limit": limit,
        "unread_only": False
    }
    
    response = requests.get(url, headers=HEADERS, params=params)
    return print_response(response, f"获取邮件列表 ({folder})")


def test_search_emails(query="测试"):
    """测试：搜索邮件"""
    url = f"{API_BASE_URL}/emails/search"
    data = {
        "account_id": ACCOUNT_ID,
        "query": query,
        "folder": "INBOX",
        "date_from": (datetime.now() - timedelta(days=30)).isoformat(),
        "limit": 10
    }
    
    response = requests.post(url, headers=HEADERS, json=data)
    return print_response(response, f"搜索邮件 (关键词: {query})")


def test_send_email():
    """测试：发送普通邮件"""
    url = f"{API_BASE_URL}/emails/send"
    data = {
        "account_id": ACCOUNT_ID,
        "to": [TEST_RECIPIENT],
        "subject": f"API 测试邮件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "body": """
<h1>API 测试邮件</h1>
<p>这是一封通过 <strong>Exchange 邮件网关 API</strong> 发送的测试邮件。</p>
<p>发送时间：{}</p>
<hr>
<p style="color: #666;">此邮件由自动化脚本发送，请勿回复。</p>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        "body_type": "html",
        "save_to_sent": True
    }
    
    response = requests.post(url, headers=HEADERS, json=data)
    return print_response(response, "发送普通邮件")


def test_send_email_with_attachment():
    """测试：发送带附件的邮件"""
    import base64
    
    url = f"{API_BASE_URL}/emails/send"
    
    # 创建一个简单的文本附件
    attachment_content = "这是附件内容\n测试文件\n" + datetime.now().isoformat()
    b64_content = base64.b64encode(attachment_content.encode()).decode()
    
    data = {
        "account_id": ACCOUNT_ID,
        "to": [TEST_RECIPIENT],
        "subject": f"带附件的测试邮件 - {datetime.now().strftime('%H:%M:%S')}",
        "body": "<p>请查看附件。</p>",
        "body_type": "html",
        "attachments": [
            {
                "filename": "test_file.txt",
                "content": b64_content,
                "content_type": "text/plain"
            }
        ]
    }
    
    response = requests.post(url, headers=HEADERS, json=data)
    return print_response(response, "发送带附件邮件")


# =========================================================================
# 模板发送测试
# =========================================================================

def test_send_template(template_id=1):
    """
    测试：使用模板发送邮件
    
    模板变量会被自动替换：
    - {{name}} -> 收件人姓名
    - {{file_name}} -> 文件名称
    """
    url = f"{API_BASE_URL}/emails/send-template"
    data = {
        "template_id": template_id,
        "account_id": ACCOUNT_ID,
        "to": [TEST_RECIPIENT],
        "variables": {
            "name": "张经理",
            "file_name": "《品牌宣传指南 v2.0》"
        }
    }
    
    response = requests.post(url, headers=HEADERS, json=data)
    return print_response(response, f"使用模板发送邮件 (template_id={template_id})")


# =========================================================================
# 速率限制测试
# =========================================================================

def test_rate_limit(requests_count=5):
    """测试：速率限制功能"""
    url = f"{API_BASE_URL}/emails/folders/list"
    params = {"account_id": ACCOUNT_ID}
    
    print(f"\n{'='*60}")
    print(f"  速率限制测试 (连续请求 {requests_count} 次)")
    print(f"{'='*60}")
    
    for i in range(requests_count):
        response = requests.get(url, headers=HEADERS, params=params)
        rate_limit = response.headers.get("X-RateLimit-Limit", "N/A")
        rate_remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
        print(f"  [{i+1}] Status: {response.status_code}, "
              f"Limit: {rate_limit}, Remaining: {rate_remaining}")
        
        if response.status_code == 429:
            print(f"    ⚠️ 速率限制触发!")
            data = response.json()
            print(f"    Message: {data.get('msg', data.get('detail', 'N/A'))}")
            break


# =========================================================================
# 主测试流程
# =========================================================================

def run_basic_tests():
    """运行基础功能测试"""
    print_section("基础功能测试")
    
    # 1. 获取文件夹列表
    test_list_folders()
    
    # 2. 获取收件箱邮件
    test_list_emails("INBOX", 3)
    
    # 3. 搜索邮件
    test_search_emails("API")


def run_send_tests():
    """运行发送功能测试"""
    print_section("邮件发送测试")
    
    # 1. 发送普通邮件
    test_send_email()
    
    # 2. 发送带附件邮件 (取消注释以测试)
    # test_send_email_with_attachment()


def run_template_tests():
    """运行模板发送测试"""
    print_section("模板发送测试")
    
    # 使用模板 ID 1 发送
    # 请确保模板已创建且包含 {{name}} 和 {{file_name}} 变量
    test_send_template(template_id=1)


def run_rate_limit_test():
    """运行速率限制测试"""
    print_section("速率限制测试")
    test_rate_limit(5)


def main():
    print(f"\n{'*'*70}")
    print(f"  Exchange 邮件网关 API 测试")
    print(f"  API URL: {API_BASE_URL}")
    print(f"  API Key: {API_KEY[:8]}...")
    print(f"  Account ID: {ACCOUNT_ID}")
    print(f"  Test Recipient: {TEST_RECIPIENT}")
    print(f"{'*'*70}")
    
    # 运行测试套件
    run_basic_tests()
    run_send_tests()
    run_template_tests()
    run_rate_limit_test()
    
    print("\n\n✅ 测试完成!")


if __name__ == "__main__":
    main()
