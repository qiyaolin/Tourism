from html import escape
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.itinerary_service import get_public_itinerary_share_meta

router = APIRouter(tags=["share"])


def _build_og_html(
    *,
    title: str,
    description: str,
    cover_image_url: str | None,
    public_url: str,
) -> str:
    safe_title = escape(title)
    safe_description = escape(description)
    safe_public_url = escape(public_url, quote=True)
    image_meta = ""
    if cover_image_url:
        safe_image_url = escape(cover_image_url, quote=True)
        image_meta = f'<meta property="og:image" content="{safe_image_url}"/>'
    return (
        "<!doctype html>"
        '<html lang="zh-CN">'
        "<head>"
        '<meta charset="UTF-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        f"<title>{safe_title}</title>"
        f'<meta name="description" content="{safe_description}"/>'
        f'<meta property="og:title" content="{safe_title}"/>'
        f'<meta property="og:description" content="{safe_description}"/>'
        f"{image_meta}"
        f'<meta property="og:url" content="{safe_public_url}"/>'
        '<meta property="og:type" content="website"/>'
        f'<link rel="canonical" href="{safe_public_url}"/>'
        f'<meta http-equiv="refresh" content="0;url={safe_public_url}"/>'
        "</head>"
        "<body>"
        f'<p>正在跳转到公开行程页：<a href="{safe_public_url}">{safe_title}</a></p>'
        "</body>"
        "</html>"
    )


@router.get("/share/itineraries/{itinerary_id}", response_class=HTMLResponse)
def itinerary_share_card(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    meta = get_public_itinerary_share_meta(db, itinerary_id)
    html = _build_og_html(
        title=meta.title,
        description=meta.description,
        cover_image_url=meta.cover_image_url,
        public_url=meta.public_url,
    )
    return HTMLResponse(content=html)
