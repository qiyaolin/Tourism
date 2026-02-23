from app.api.share import _build_og_html


def test_build_og_html_contains_required_tags():
    html = _build_og_html(
        title="北京周末计划",
        description="北京 · 2 天 · 作者 小王",
        cover_image_url="https://example.com/cover.jpg",
        public_url="http://localhost:5173/itineraries/abc",
    )

    assert 'property="og:title"' in html
    assert 'property="og:description"' in html
    assert 'property="og:image"' in html
    assert 'property="og:url"' in html
    assert 'http-equiv="refresh"' in html
