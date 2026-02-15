import requests
import json
import time

# =============================================================================
# 配置区域 (请在此处填写您的测试信息)
# =============================================================================
BASE_URL = "http://localhost:9997/api/v1/exchange"

# 请确保 API Key 拥有以下权限: ["contacts", "send", "receive", "reply", "search"]
API_KEY = "ec5e20cc75a3821564a5c7cd049a2c3970dbc7e685eeafaaf8d010940ac174c0" 

# 测试用的邮箱账户 ID
ACCOUNT_ID = 6

# 用于测试模板发送的模板 ID (如果不想测试此项，可留空或设为 0)
TEMPLATE_ID = "随便测试"

# 测试发送/回复的目标邮箱 (通常建议发给自己)
TEST_RECIPIENT_EMAIL = "q-fu@tianjin-air.com"

# =============================================================================
# 测试脚本
# =============================================================================

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def log(msg, type="INFO"):
    print(f"[{type}] {msg}")

def test_gal_integration():
    """测试通讯录集成 (Feature 2)"""
    log("=== 开始测试: GAL 通讯录集成 ===")
    
    # 用户指定测试: "yy-zhang1@tianjin-air.com"
    query = "yy-zhang1@tianjin-air.com"
    
    url = f"{BASE_URL}/contacts/resolve"
    params = {
        "q": query,
        "account_id": ACCOUNT_ID
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            # contacts endpoint returns explicit boolean success
            if data.get('success'):
                contacts = data['data']
                log(f"搜索 '{query}' 成功，找到 {len(contacts)} 个联系人:")
                for c in contacts:
                    log(f"  - {c['name']} <{c['email']}> ({c.get('mailbox_type')})")
            else:
                log(f"查询返回失败: {data['message']}", "ERROR")
        else:
            log(f"HTTP 请求失败: {response.status_code} - {response.text}", "ERROR")
    except Exception as e:
        log(f"发生异常: {e}", "ERROR")
    log("================================\n")

def test_rich_template():
    """测试富文本模板发送 (Feature 1)"""
    log("=== 开始测试: 富文本模板发送 ===")
    
    if not TEMPLATE_ID:
        log("跳过 (未配置 TEMPLATE_ID)", "WARN")
        return

    url = f"{BASE_URL}/emails/send-template"
    payload = {
        "account_id": ACCOUNT_ID,
        "template_name": TEMPLATE_ID,  # 现在支持模板名称
        "to": [TEST_RECIPIENT_EMAIL],
        "variables": {
            "name": "Integration Tester",
            "date": "2026-02-09"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            # Standard Success response uses code=200
            if data.get('code') == 200:
                log(f"模板邮件发送成功! Log ID: {data['data']['log_id']}")
            else:
                log(f"发送失败: {data['message']}", "ERROR")
        else:
            log(f"HTTP 请求失败: {response.status_code} - {response.text}", "ERROR")
    except Exception as e:
        log(f"发生异常: {e}", "ERROR")
    log("================================\n")

def test_outlook_reply():
    """测试 Outlook 风格回复 (Feature 3)"""
    log("=== 开始测试: Outlook 风格回复 ===")
    
    # 1. 先发送一封测试邮件作为"原邮件"
    log("Step 1: 发送原邮件 (模拟 '降本创效' 通知)...")
    send_url = f"{BASE_URL}/emails/send"
    subject = "【请阅处】关于录入2026年1月降本创效成效的通知"
    
    # 模拟 PDF/截图中的原始内容
    original_html = """
    <html>
    <body style="font-family:'Calibri',sans-serif;font-size:11.0pt;color:#000000">
        <p>各单位：</p>
        <p>2026年1月降本创效数据，请于2月10日前在降本创效系统中录入完毕，具体请见邮件下方。</p>
        <p>2026年1月：根据航空统一要求，自2026年1月起使用系统统计降本创效数据，具体情况如下。</p>
        <p>1.系统地址和日记本地一致，见下方附图1。</p>
        <p>2.已开通权限见附件1，新开权限填列附件，向信息技术部申请。</p>
        <p>3.通过下载导入模板导入系统。请对接人部内收集后统一导入。</p>
        <br>
        <p>天津航空财务部成本预算中心</p>
        <p>2026年2月9日 11:30</p>
    </body>
    </html>
    """
    
    send_payload = {
        "account_id": ACCOUNT_ID,
        "to": [TEST_RECIPIENT_EMAIL],
        "subject": subject,
        "body": original_html,
        "body_type": "html"
    }
    
    try:
        # 发送
        r = requests.post(send_url, headers=headers, json=send_payload)
        if r.status_code != 200 or r.json().get('code') != 200:
            log(f"原邮件发送失败, 终止测试: {r.text}", "ERROR")
            return
            
        log("原邮件已发送，等待 10 秒以确保邮件到达并可被搜索...")
        time.sleep(10)
        
        # 2. 搜索该邮件以获取 Item ID
        log("Step 2: 搜索原邮件以获取 ID...")
        search_url = f"{BASE_URL}/emails/search"
        search_payload = {
            "account_id": ACCOUNT_ID,
            "query": subject,
            "limit": 1
        }
        
        r = requests.post(search_url, headers=headers, json=search_payload)
        search_res = r.json()
        
        item_id = None
        if search_res.get('code') == 200 and search_res.get('data', {}).get('items'):
            item_id = search_res['data']['items'][0]['id']
            log(f"找到原邮件 ID: {item_id[:20]}...")
        else:
            log("未找到原邮件，可能同步延迟，无法继续测试回复。", "WARN")
            return
            
        # 3. 回复该邮件
        log("Step 3: 发送 Outlook 风格回复...")
        reply_url = f"{BASE_URL}/emails/reply"
        
        # 模拟真实的回复内容
        real_reply_body = """
        <p>财务部同事：</p>
        <p>收到，我们已安排各部门对接人进行数据收集，会按时在系统中完成录入。</p>
        <br>
        <p>谨致问候，</p>
        <p>张阳阳(Maggie)<br>天航信息技术部</p>
        """
        
        reply_payload = {
            "account_id": ACCOUNT_ID,
            "reference_item_id": item_id,
            "to": [TEST_RECIPIENT_EMAIL],
            "subject": f"Re: {subject}",
            "body": real_reply_body,
            "body_type": "html",
            "reply_all": False
        }
        
        r = requests.post(reply_url, headers=headers, json=reply_payload)
        reply_res = r.json()
        
        if reply_res.get('code') == 200:
            log("回复发送成功！请登录 Outlook 检查邮件格式是否包含灰色分割线和完整头部。")
        else:
            log(f"回复发送失败: {reply_res.get('message')}", "ERROR")

    except Exception as e:
        log(f"发生异常: {e}", "ERROR")
    log("================================\n")

if __name__ == "__main__":
    print("开始集成测试...\n")
    # test_gal_integration()
    test_rich_template()
    # test_outlook_reply()
