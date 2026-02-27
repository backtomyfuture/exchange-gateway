from app.services.exchange.format_utils import _extract_body_content, process_inline_images


def test_extract_body_with_style():
    html = """<html><head><style>.foo { color: red; }</style></head>
    <body><p>Hello</p></body></html>"""
    styles, body = _extract_body_content(html)
    assert "<style>" in styles
    assert "color: red" in styles
    assert "<p>Hello</p>" in body
    assert "<body" not in body


def test_extract_body_without_body_tag():
    html = "<div>No body tag here</div>"
    styles, body = _extract_body_content(html)
    assert styles == ""
    assert "No body tag here" in body


def test_extract_body_empty():
    styles, body = _extract_body_content("")
    assert styles == ""
    assert body == ""


def test_process_inline_images_no_images():
    html = '<p>Hello <img src="http://example.com/img.png"></p>'
    new_html, attachments = process_inline_images(html)
    assert new_html == html
    assert attachments == []


def test_process_inline_images_with_base64():
    b64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    html = f'<img src="data:image/png;base64,{b64_data}">'
    new_html, attachments = process_inline_images(html)
    assert len(attachments) == 1
    assert "cid:" in new_html
    assert "data:image" not in new_html
    att = attachments[0]
    assert att["content_type"] == "image/png"
    assert att["content"] == b64_data
    assert att["content_id"].endswith("@exchange.internal")
    assert att["filename"].endswith(".png")
