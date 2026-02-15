import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.exchange.template_service import TemplateService

async def test_render():
    service = TemplateService()
    
    # Test case 1: Simple HTML
    template_html = "<h1>Hello {{ name }}</h1><p>Welcome to {{ corp }}</p>"
    variables = {"name": "Jarod", "corp": "Google"}
    
    rendered = service._replace_variables(template_html, variables)
    print(f"Original: {template_html}")
    print(f"Rendered: {rendered}")
    
    assert "Hello Jarod" in rendered
    assert "Welcome to Google" in rendered
    
    # Test case 2: Complex HTML with attributes
    template_html_2 = '<a href="{{ link }}">Click Here</a>'
    variables_2 = {"link": "https://google.com"}
    rendered_2 = service._replace_variables(template_html_2, variables_2)
    print(f"Original: {template_html_2}")
    print(f"Rendered: {rendered_2}")
    
    assert 'href="https://google.com"' in rendered_2

    print("\nAll Jinja2 tests passed!")

if __name__ == "__main__":
    asyncio.run(test_render())
