"""add collab share code columns

Revision ID: 20260221_0013
Revises: 20260220_0012
Create Date: 2026-02-21 09:20:00
"""

from __future__ import annotations

import hashlib
import os
import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260221_0013"
down_revision: str | None = "20260220_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _hash_share_code(code: str, secret: str) -> str:
    digest = hashlib.sha256()
    digest.update(secret.encode("utf-8"))
    digest.update(b":share_code:")
    digest.update(code.encode("utf-8"))
    return digest.hexdigest()


def _generate_share_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(8))


def upgrade() -> None:
    op.add_column(
        "itinerary_collab_links",
        sa.Column("share_code_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "itinerary_collab_links",
        sa.Column("share_code_last4", sa.String(length=4), nullable=True),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM itinerary_collab_links")).all()
    secret = os.getenv("COLLAB_TOKEN_SECRET", "replace-with-dev-collab-secret")
    used_hashes: set[str] = set()
    for row in rows:
        while True:
            share_code = _generate_share_code()
            share_hash = _hash_share_code(share_code, secret)
            if share_hash in used_hashes:
                continue
            used_hashes.add(share_hash)
            conn.execute(
                sa.text(
                    "UPDATE itinerary_collab_links "
                    "SET share_code_hash=:share_code_hash, share_code_last4=:share_code_last4 "
                    "WHERE id=:id"
                ),
                {
                    "id": row.id,
                    "share_code_hash": share_hash,
                    "share_code_last4": share_code[-4:],
                },
            )
            break

    op.alter_column("itinerary_collab_links", "share_code_hash", nullable=False)
    op.alter_column("itinerary_collab_links", "share_code_last4", nullable=False)
    op.create_index(
        op.f("ix_itinerary_collab_links_share_code_hash"),
        "itinerary_collab_links",
        ["share_code_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_itinerary_collab_links_share_code_hash"),
        table_name="itinerary_collab_links",
    )
    op.drop_column("itinerary_collab_links", "share_code_last4")
    op.drop_column("itinerary_collab_links", "share_code_hash")
