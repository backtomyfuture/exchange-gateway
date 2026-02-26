"""
邮件格式化工具
用于生成 Outlook 风格的回复/转发头部，以及处理内联图片

字体策略 (中文商务最佳实践):
  - Calibri: Outlook 默认 Latin 字体
  - 等线/DengXian: Outlook 2016+ 默认 CJK 字体
  - 微软雅黑: 现代中文UI字体
  - 宋体/SimSun: 经典中文正式字体（兜底）
"""

import re
import uuid

from exchangelib.items import Item

# 中文商务邮件标准字体栈
FONT_STACK = "'Calibri','等线','DengXian','微软雅黑','Microsoft YaHei','宋体','SimSun',sans-serif"
FONT_SIZE = "11.0pt"
FONT_COLOR = "#000000"


def _extract_body_content(html: str) -> tuple[str, str]:
    """
    从 HTML 中安全提取 <style> 块和 <body> 内部内容。

    确保原始邮件的所有格式信息（CSS、内联样式等）被完整保留，
    同时避免 <html>/<body> 标签嵌套。

    Args:
        html: 原始 HTML 字符串

    Returns:
        (style_blocks, body_content):
            - style_blocks: 从 <head> 中提取的所有 <style>...</style> 标签（含标签本身）
            - body_content: <body> 内部的 HTML 内容（不含 <body> 标签本身）
    """
    if not html:
        return "", ""

    # 1. 提取所有 <style> 块（可能在 <head> 或 <body> 中）
    style_pattern = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
    style_matches = style_pattern.findall(html)
    style_blocks = "\n".join(style_matches) if style_matches else ""

    # 2. 提取 <body> 内部内容
    body_pattern = re.compile(r"<body[^>]*>(.*)</body>", re.DOTALL | re.IGNORECASE)
    body_match = body_pattern.search(html)

    if body_match:
        body_content = body_match.group(1).strip()
    else:
        # 没有 <body> 标签，尝试去除 <html> 和 <head>
        content = html
        content = re.sub(r"<html[^>]*>", "", content, flags=re.IGNORECASE)
        content = re.sub(r"</html>", "", content, flags=re.IGNORECASE)
        content = re.sub(r"<head[^>]*>.*?</head>", "", content, flags=re.DOTALL | re.IGNORECASE)
        # 移除已提取的 style 块避免重复（它们已保存在 style_blocks 中）
        for s in style_matches:
            content = content.replace(s, "", 1)
        body_content = content.strip()

    return style_blocks, body_content


def build_outlook_reply_header(
    original_item: Item, reply_body: str, is_reply_all: bool = False, is_forward: bool = False
) -> str:
    """
    构建 Outlook 风格的回复/转发邮件完整 HTML。

    输出结构：
        <html>
          <head>
            <meta charset="UTF-8">
            <!-- 原始邮件的 <style> 块 -->
          </head>
          <body>
            <!-- 用户的新回复内容 (中文商务字体) -->
            <div style="font-family:...;font-size:11pt;color:#000">
              {reply_body}
            </div>
            <br>
            <!-- Outlook 风格分隔线 + 邮件头 -->
            <div style="border-top:solid #E1E1E1 1.0pt;...">
              <p>发件人: / 发送时间: / 收件人: / 主题:</p>
            </div>
            <br>
            <!-- 原始邮件正文 (原封不动) -->
            {original_body_content}
          </body>
        </html>

    Args:
        original_item: 原始邮件对象 (exchangelib Item)
        reply_body: 用户输入的回复内容 (HTML 片段)
        is_reply_all: 是否全部回复
        is_forward: 是否转发

    Returns:
        包含 Outlook 头部的完整 HTML 文档字符串
    """

    # =========================================================================
    # 1. 提取原始邮件元数据
    # =========================================================================
    sender_name = original_item.sender.name if original_item.sender else "Unknown"
    sender_email = original_item.sender.email_address if original_item.sender else ""

    # 时间格式化: Outlook 中文版 "2026年2月9日 15:30" (无前导零)
    sent_time_str = ""
    if original_item.datetime_received:
        dt = original_item.datetime_received
        # %-m / %-d 在 Linux 下去除前导零 (Docker 环境)
        try:
            sent_time_str = dt.strftime("%Y{y}%-m{m}%-d{d} %H:%M").format(y="年", m="月", d="日")
        except ValueError:
            # Windows 等不支持 %-m 的平台兜底
            sent_time_str = f"{dt.year}年{dt.month}月{dt.day}日 {dt.strftime('%H:%M')}"

    def format_recipient(r):
        """格式化收件人为 'Name <email>' 格式"""
        if r.name and r.email_address and r.name != r.email_address:
            return f"{r.name} &lt;{r.email_address}&gt;"
        return r.name or r.email_address or ""

    to_str = ""
    if original_item.to_recipients:
        to_str = "; ".join([format_recipient(r) for r in original_item.to_recipients])

    cc_str = ""
    if original_item.cc_recipients:
        cc_str = "; ".join([format_recipient(r) for r in original_item.cc_recipients])

    subject = original_item.subject or ""

    # =========================================================================
    # 2. 构建 Outlook 风格分割线 + 邮件头
    # =========================================================================
    # 样式参照 Outlook 2019/365 中文版实际输出:
    # - 顶部实线边框 #E1E1E1
    # - MsoNormal 段落类
    # - Calibri + 中文字体栈
    header_lines = [
        '<div style="border:none;border-top:solid #E1E1E1 1.0pt;padding:3.0pt 0cm 0cm 0cm">',
        f'  <p class="MsoNormal" style="margin:0cm;font-size:{FONT_SIZE};font-family:{FONT_STACK}">',
        f"    <b>发件人:</b> {sender_name} &lt;{sender_email}&gt;<br>",
        f"    <b>发送时间:</b> {sent_time_str}<br>",
        f"    <b>收件人:</b> {to_str}<br>",
    ]

    if cc_str:
        header_lines.append(f"    <b>抄送:</b> {cc_str}<br>")

    header_lines.extend(
        [
            f"    <b>主题:</b> {subject}<br>",
            "  </p>",
            "</div>",
        ]
    )

    header_html = "\n".join(header_lines)

    # =========================================================================
    # 3. 处理原始邮件正文 (零损失保留)
    # =========================================================================
    original_body_raw = ""
    if isinstance(original_item.body, str):
        original_body_raw = original_item.body
    elif hasattr(original_item, "text_body") and original_item.text_body:
        original_body_raw = f"<pre>{original_item.text_body}</pre>"

    # 安全提取原始邮件的 <style> 和 <body> 内容
    original_styles, original_body_content = _extract_body_content(original_body_raw)

    # =========================================================================
    # 4. 包装用户回复内容 (中文商务正式风格)
    # =========================================================================
    styled_reply_body = (
        f'<div style="font-family:{FONT_STACK};font-size:{FONT_SIZE};color:{FONT_COLOR}">\n  {reply_body}\n</div>'
    )

    # =========================================================================
    # 5. 组装完整 HTML 文档
    # =========================================================================
    full_html = (
        f"<html>\n"
        f"<head>\n"
        f'  <meta charset="UTF-8">\n'
        f"  {original_styles}\n"
        f"</head>\n"
        f"<body>\n"
        f"{styled_reply_body}\n"
        f"<br>\n"
        f"{header_html}\n"
        f"<br>\n"
        f"{original_body_content}\n"
        f"</body>\n"
        f"</html>"
    )

    return full_html


def process_inline_images(html_content: str) -> tuple[str, list[dict]]:
    """
    解析 HTML 中的 Base64 图片，并将其转换为 CID 引用格式。

    用于发送前将 Base64 内嵌图片提取为独立附件，
    解决 Outlook 对 data URI 兼容性差的问题。

    Returns:
        Tuple[new_html, attachments_to_add]
        attachments_to_add: 列表，每个元素包含 {filename, content, content_type, content_id}
    """
    if not html_content:
        return html_content, []

    # 匹配 data:image 类型的 Base64 图片
    # 支持 src=" / src=' / src= (wangEditor 可能输出不带引号的 src)
    pattern = r'src=["\']?\s*data:(image/[^;]+);base64,([^"\'\s>]+)["\']?'

    attachments = []
    from app.log import logger

    def replace_func(match):
        content_type = match.group(1).strip()
        base64_data = match.group(2).strip()

        # 移除 Base64 中的空白字符（如换行符）
        base64_data = "".join(base64_data.split())

        # 生成唯一 CID
        cid = f"img_{uuid.uuid4().hex[:8]}@exchange.internal"

        # 生成扩展名
        ext = content_type.split("/")[-1] if "/" in content_type else "png"
        filename = f"inline_{uuid.uuid4().hex[:4]}.{ext}"

        attachments.append(
            {"filename": filename, "content": base64_data, "content_type": content_type, "content_id": cid}
        )

        logger.info(f"提取 Base64 图片: {filename}, CID: {cid}, 长度: {len(base64_data)}")
        return f'src="cid:{cid}"'

    # 使用 re.DOTALL 标志
    new_html = re.sub(pattern, replace_func, html_content, flags=re.DOTALL | re.IGNORECASE)

    if len(attachments) > 0:
        logger.info(f"HTML 处理完成: 替换了 {len(attachments)} 个图片，新长度: {len(new_html)}")

    return new_html, attachments
