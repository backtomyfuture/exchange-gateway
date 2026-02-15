"""
TemplateService 单元测试
测试邮件模板管理功能
注意：仅测试不依赖 ORM 的功能（如模板渲染）
"""
import pytest
from unittest.mock import patch

from app.services.exchange.template_service import TemplateService, get_template_service


# ========================================
# 基础功能测试
# ========================================

def test_get_template_service_singleton():
    """测试模板服务单例模式"""
    svc1 = get_template_service()
    svc2 = get_template_service()
    assert svc1 is svc2


def test_template_service_initialization():
    """测试服务初始化"""
    svc = TemplateService()
    assert svc is not None


def test_template_service_variable_pattern():
    """测试变量正则表达式"""
    svc = TemplateService()
    pattern = svc.VARIABLE_PATTERN
    
    # 测试能匹配 {{variable}} 格式
    match = pattern.search("Hello {{ name }}")
    assert match is not None
    assert match.group(1) == "name"
    
    # 测试能匹配无空格的格式
    match = pattern.search("Hello {{name}}")
    assert match is not None
    assert match.group(1) == "name"


# ========================================
# 模板渲染测试（纯函数测试）
# ========================================

def test_replace_variables_basic():
    """测试基本变量替换"""
    svc = TemplateService()
    text = "Hello, {{ name }}! Welcome to {{ company }}."
    variables = {"name": "John", "company": "ACME"}
    
    result = svc._replace_variables(text, variables)
    
    assert result == "Hello, John! Welcome to ACME."


def test_replace_variables_no_space():
    """测试无空格变量替换"""
    svc = TemplateService()
    text = "Hello, {{name}}! Welcome to {{company}}."
    variables = {"name": "John", "company": "ACME"}
    
    result = svc._replace_variables(text, variables)
    
    assert result == "Hello, John! Welcome to ACME."


def test_replace_variables_missing():
    """测试缺少变量时保持原样"""
    svc = TemplateService()
    text = "Hello, {{ name }}! Your code is {{ code }}."
    variables = {"name": "John"}  # 缺少 code
    
    result = svc._replace_variables(text, variables)
    
    assert "John" in result
    assert "{{ code }}" in result  # 缺少的变量保持原样


def test_replace_variables_empty():
    """测试空变量字典"""
    svc = TemplateService()
    text = "Hello, World! No variables here."
    variables = {}
    
    result = svc._replace_variables(text, variables)
    
    assert result == "Hello, World! No variables here."


def test_replace_variables_html():
    """测试 HTML 内容中的变量替换"""
    svc = TemplateService()
    text = "<html><body><h1>{{ title }}</h1><p>{{ content }}</p></body></html>"
    variables = {"title": "Welcome", "content": "This is a test."}
    
    result = svc._replace_variables(text, variables)
    
    assert "<h1>Welcome</h1>" in result
    assert "<p>This is a test.</p>" in result


def test_replace_variables_special_chars():
    """测试特殊字符值"""
    svc = TemplateService()
    text = "Price: {{ price }}"
    variables = {"price": "$100.00"}
    
    result = svc._replace_variables(text, variables)
    
    assert result == "Price: $100.00"


def test_replace_variables_multiple_same():
    """测试多次使用同一变量"""
    svc = TemplateService()
    text = "{{ name }} said hello. {{ name }} is here."
    variables = {"name": "Alice"}
    
    result = svc._replace_variables(text, variables)
    
    assert result == "Alice said hello. Alice is here."


def test_replace_variables_chinese():
    """测试中文变量值"""
    svc = TemplateService()
    text = "尊敬的 {{ name }}，您好！"
    variables = {"name": "张三"}
    
    result = svc._replace_variables(text, variables)
    
    assert result == "尊敬的 张三，您好！"


def test_replace_variables_empty_value():
    """测试空字符串变量值"""
    svc = TemplateService()
    text = "Hello, {{ name }}!"
    variables = {"name": ""}
    
    result = svc._replace_variables(text, variables)
    
    assert result == "Hello, !"
