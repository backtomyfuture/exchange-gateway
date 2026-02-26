from app.schemas.common import Page, PageParams


def test_page_params_defaults():
    p = PageParams()
    assert p.page == 1
    assert p.size == 20
    assert p.offset == 0


def test_page_params_offset():
    p = PageParams(page=3, size=10)
    assert p.offset == 20


def test_page_params_clamps_size():
    p = PageParams(size=200)
    assert p.size == 100  # max is 100


def test_page_total_pages():
    page = Page[str](items=["a", "b"], total=100, page=1, size=3)
    assert page.pages == 34  # ceil(100/3)


def test_page_params_skip_limit_backward_compat():
    """Legacy skip/limit are converted to page/size."""
    p = PageParams(skip=20, limit=10)
    assert p.size == 10
    assert p.offset == 20
