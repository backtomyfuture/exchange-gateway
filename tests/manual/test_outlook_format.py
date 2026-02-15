"""
测试 Outlook 风格回复/转发格式

验证:
1. 中文商务字体栈正确应用
2. 原始邮件格式完整保留（含 <style> 块）
3. <html>/<body> 标签不嵌套
4. 分隔线和邮件头正确生成
"""
import sys
import os
from unittest.mock import MagicMock
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.services.exchange.format_utils import (
    build_outlook_reply_header,
    _extract_body_content,
    FONT_STACK,
    process_inline_images,
)


def test_extract_body_content():
    """测试 HTML body 内容提取"""
    print("=== 测试 _extract_body_content ===")
    
    # 测试1: 完整 HTML 文档
    html = """
    <html>
    <head>
        <style>.important { color: red; font-weight: bold; }</style>
        <meta charset="UTF-8">
    </head>
    <body class="custom-body">
        <p>Hello World</p>
        <table><tr><td>Data</td></tr></table>
    </body>
    </html>
    """
    styles, body = _extract_body_content(html)
    assert ".important { color: red;" in styles, f"Style block not extracted: {styles}"
    assert "<p>Hello World</p>" in body, f"Body content not extracted: {body}"
    assert "<html>" not in body, "Should not contain <html> tag"
    assert "<body" not in body, "Should not contain <body> tag"
    print("  ✅ 完整 HTML 文档: style 和 body 正确提取")
    
    # 测试2: 无 body 标签的纯 HTML 片段
    html2 = "<div><p>Simple content</p></div>"
    styles2, body2 = _extract_body_content(html2)
    assert "Simple content" in body2
    assert styles2 == ""
    print("  ✅ 纯 HTML 片段: 直接返回内容")
    
    # 测试3: 空字符串
    styles3, body3 = _extract_body_content("")
    assert styles3 == "" and body3 == ""
    print("  ✅ 空字符串: 安全返回")
    
    # 测试4: 多个 style 块
    html4 = """
    <html><head>
        <style>body { margin: 0; }</style>
        <style>.table { border: 1px solid black; }</style>
    </head><body><p>Content</p></body></html>
    """
    styles4, body4 = _extract_body_content(html4)
    assert "margin: 0" in styles4
    assert "border: 1px solid black" in styles4
    print("  ✅ 多个 style 块: 全部保留")
    
    print("=== _extract_body_content 全部通过 ===\n")


def test_outlook_reply_header_chinese_fonts():
    """测试中文商务字体栈"""
    print("=== 测试中文商务字体栈 ===")
    
    mock_item = MagicMock()
    mock_item.sender.name = "张三"
    mock_item.sender.email_address = "zhangsan@example.com"
    mock_item.datetime_received = datetime(2026, 2, 9, 15, 30)
    mock_item.to_recipients = [MagicMock(name="李四", email_address="lisi@example.com")]
    mock_item.cc_recipients = []
    mock_item.subject = "关于2026年Q1项目计划"
    mock_item.body = "<p>请查收附件中的项目计划。</p>"
    
    reply_body = "<p>收到，已阅。谢谢！</p>"
    full_body = build_outlook_reply_header(mock_item, reply_body)
    
    # 验证字体栈
    assert "'等线'" in full_body, "Should contain DengXian (等线)"
    assert "'微软雅黑'" in full_body, "Should contain Microsoft YaHei"
    assert "'宋体'" in full_body, "Should contain SimSun"
    assert "'Calibri'" in full_body, "Should contain Calibri"
    print("  ✅ 用户回复部分: 包含完整中文商务字体栈")
    
    # 验证头部也使用了中文字体栈
    assert "font-family:" in full_body
    print("  ✅ 邮件头: 使用统一字体栈")
    
    # 验证字号
    assert "11.0pt" in full_body
    print("  ✅ 字号: 11pt (Outlook 标准)")
    
    # 验证颜色
    assert "#000000" in full_body
    print("  ✅ 颜色: #000000")
    
    print("=== 中文商务字体栈全部通过 ===\n")


def test_outlook_reply_header_format():
    """测试回复头部格式"""
    print("=== 测试回复头部格式 ===")
    
    mock_item = MagicMock()
    mock_item.sender.name = "王磊"
    mock_item.sender.email_address = "wanglei@tianjin-air.com"
    mock_item.datetime_received = datetime(2026, 2, 9, 15, 30)
    
    mock_to = MagicMock()
    mock_to.name = "张阳阳(Maggie)"
    mock_to.email_address = "yy-zhang1@tianjin-air.com"
    mock_item.to_recipients = [mock_to]
    
    mock_cc = MagicMock()
    mock_cc.name = "天航信息技术部"
    mock_cc.email_address = "thxxcxb@hnair.com"
    mock_item.cc_recipients = [mock_cc]
    
    mock_item.subject = "Re: 关于系统升级通知"
    mock_item.body = "<p>原始邮件内容保持不变。</p>"
    
    full_body = build_outlook_reply_header(mock_item, "<p>收到。</p>")
    
    # 验证分隔线
    assert "border-top:solid #E1E1E1 1.0pt" in full_body
    print("  ✅ 分隔线: solid #E1E1E1 1.0pt")
    
    # 验证中文标签
    assert "<b>发件人:</b>" in full_body
    assert "<b>发送时间:</b>" in full_body
    assert "<b>收件人:</b>" in full_body
    assert "<b>抄送:</b>" in full_body
    assert "<b>主题:</b>" in full_body
    print("  ✅ 中文标签: 发件人/发送时间/收件人/抄送/主题")
    
    # 验证收件人格式
    assert "张阳阳(Maggie) &lt;yy-zhang1@tianjin-air.com&gt;" in full_body
    print("  ✅ 收件人格式: Name <email>")
    
    # 验证原始内容
    assert "原始邮件内容保持不变。" in full_body
    print("  ✅ 原始内容: 完整保留")
    
    print("=== 回复头部格式全部通过 ===\n")


def test_original_format_preservation():
    """测试原始邮件格式保留"""
    print("=== 测试原始邮件格式保留 ===")
    
    mock_item = MagicMock()
    mock_item.sender.name = "System"
    mock_item.sender.email_address = "system@example.com"
    mock_item.datetime_received = datetime(2026, 2, 9, 10, 0)
    mock_item.to_recipients = [MagicMock(name="User", email_address="user@example.com")]
    mock_item.cc_recipients = []
    mock_item.subject = "System Report"
    
    # 模拟复杂的原始邮件 HTML (含 <html>/<head>/<style>/<body>)
    mock_item.body = """
    <html>
    <head>
        <style>
            .alert { color: red; font-weight: bold; }
            table.report { border-collapse: collapse; border: 1px solid #ccc; }
            table.report td { padding: 8px; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <h2 class="alert">⚠️ 重要通知</h2>
        <table class="report">
            <tr><th>模块</th><th>状态</th></tr>
            <tr><td>数据库</td><td style="color: green;">正常</td></tr>
            <tr><td>API服务</td><td style="color: orange;">告警</td></tr>
        </table>
        <p style="font-family: '宋体'; font-size: 10pt;">天津航空 IT 运维中心</p>
    </body>
    </html>
    """
    
    full_body = build_outlook_reply_header(mock_item, "<p>已处理。</p>")
    
    # 验证: 不嵌套 <html>/<body>
    assert full_body.count("<html>") == 1, f"Should have exactly 1 <html> tag, found {full_body.count('<html>')}"
    assert full_body.count("<body>") == 1, f"Should have exactly 1 <body> tag, found {full_body.count('<body>')}"
    print("  ✅ HTML 结构: 无嵌套 <html>/<body> 标签")
    
    # 验证: <style> 块保留
    assert ".alert { color: red;" in full_body
    assert "table.report" in full_body
    print("  ✅ Style 块: 保留在 <head> 中")
    
    # 验证: 原始内容保留
    assert "⚠️ 重要通知" in full_body
    assert '<td style="color: green;">正常</td>' in full_body
    assert '<td style="color: orange;">告警</td>' in full_body
    assert "font-family: '宋体'" in full_body
    print("  ✅ 原始内容: 表格、内联样式、中文字体全部保留")
    
    # 验证整体结构
    assert full_body.index("<html>") < full_body.index("<head>")
    assert full_body.index("<head>") < full_body.index("<body>")
    assert full_body.index("已处理") < full_body.index("重要通知")
    print("  ✅ 文档结构: <html> > <head> > <body>，回复在前，原文在后")
    
    print("=== 原始邮件格式保留全部通过 ===\n")


def test_process_inline_images():
    """测试 Base64 图片处理"""
    print("=== 测试 process_inline_images ===")
    
    html_with_img = '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUh" alt="test">'
    new_html, attachments = process_inline_images(html_with_img)
    
    assert len(attachments) == 1
    assert 'cid:' in new_html
    assert 'data:image' not in new_html
    assert attachments[0]["content_type"] == "image/png"
    print("  ✅ Base64 图片: 成功转换为 CID 引用")
    
    # 测试空内容
    html_empty, atts_empty = process_inline_images("")
    assert html_empty == "" and atts_empty == []
    print("  ✅ 空内容: 安全返回")
    
    print("=== process_inline_images 全部通过 ===\n")


if __name__ == "__main__":
    print("=" * 60)
    print("  Outlook 格式化工具测试")
    print("=" * 60 + "\n")
    
    test_extract_body_content()
    test_outlook_reply_header_chinese_fonts()
    test_outlook_reply_header_format()
    test_original_format_preservation()
    test_process_inline_images()
    
    print("=" * 60)
    print("  🎉 全部测试通过!")
    print("=" * 60)
