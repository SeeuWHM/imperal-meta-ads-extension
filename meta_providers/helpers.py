"""Meta Ads · Shared constants and account helpers."""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

from imperal_sdk import Context

# ─── Microservice ─────────────────────────────────────────────────────────── #

META_API_URL = os.getenv("META_API_URL", "https://api.webhostmost.com/meta-ads")
META_JWT     = os.getenv("META_JWT",     "")

# ─── OAuth constants (Phase 2 — Auth Gateway callback not yet implemented) ─── #
# When per-user OAuth is ready, set these env vars and implement token_refresh.py

META_APP_ID       = os.getenv("META_APP_ID",       "1662599881607889")
META_APP_SECRET   = os.getenv("META_APP_SECRET",   "")
META_CLIENT_ID    = os.getenv("META_CLIENT_ID",    "")   # same as META_APP_ID when configured
META_REDIRECT_URI = os.getenv(
    "META_REDIRECT_URI",
    "https://auth.imperal.io/v1/oauth/meta-ads/callback",
)
META_AUTH_URL  = "https://www.facebook.com/v21.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"
META_SCOPE     = "ads_management,ads_read,business_management"

# ─── Storage ──────────────────────────────────────────────────────────────── #

COLLECTION = "meta_ads_accounts"   # ext_store collection name
SECTION    = "meta_ads_account"    # skeleton section key


# ─── OAuth state (for Phase 2) ────────────────────────────────────────────── #

def _oauth_state(ctx: Context) -> str:
    """Encode user identity as base64url JSON for the OAuth state parameter."""
    payload = {
        "user_id":   str(ctx.user.id),
        "tenant_id": getattr(ctx.user, "tenant_id", "default"),
        "provider":  "meta-ads",
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


# ─── Account helpers ──────────────────────────────────────────────────────── #

async def _all_accounts(ctx: Context) -> list[dict]:
    """Return all meta_ads_accounts documents for the current user."""
    page = await ctx.store.query(COLLECTION)
    return [{"doc_id": d.id, **d.data} for d in page.data]


async def _active_account(ctx: Context, account: str = "") -> Optional[dict]:
    """Return the active (or specified) account dict, or None if not found.

    Lookup order when account= is given: doc_id → ad_account_id → account_name.
    Falls back to the document marked is_active, then to the first document.
    """
    page = await ctx.store.query(COLLECTION)
    if not page.data:
        return None

    if account:
        for d in page.data:
            if (d.id == account
                    or d.data.get("ad_account_id") == account
                    or d.data.get("account_name") == account):
                return {"doc_id": d.id, **d.data}
        return None

    for d in page.data:
        if d.data.get("is_active"):
            return {"doc_id": d.id, **d.data}
    return {"doc_id": page.data[0].id, **page.data[0].data}


# ─── Budget conversion helpers ─────────────────────────────────────────────── #

def dollars_to_cents(amount: float) -> int:
    """Convert user-facing dollar amount to Meta API minor units (cents)."""
    return int(round(amount * 100))


def cents_to_dollars(cents) -> float:
    """Convert Meta API minor units back to dollars for display."""
    try:
        return round(int(cents) / 100, 2)
    except (TypeError, ValueError):
        return 0.0
