"""Meta Ads · HTTP client for whm-meta-ads-control microservice.

All API calls route through this module. The microservice wraps the
facebook-business SDK; this is a thin async HTTP layer on top.

Phase 1: Server-side META_ACCESS_TOKEN (single shared token from .env).
         ad_account_id is passed per-request as a query parameter.
Phase 2: Per-user OAuth tokens via Auth Gateway (planned).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from imperal_sdk import Context

from .helpers import META_API_URL, META_JWT

log = logging.getLogger("meta-ads.client")


# ─── Internal HTTP helpers ────────────────────────────────────────────────── #

def _headers() -> dict:
    """Authorization header for all microservice requests."""
    return {"Authorization": f"Bearer {META_JWT}"}


async def _get(ctx: Context, path: str, **params) -> Any:
    r = await ctx.http.get(
        f"{META_API_URL}{path}",
        headers=_headers(),
        params={k: v for k, v in params.items() if v is not None},
    )
    r.raise_for_status()
    return r.json()


async def _post(ctx: Context, path: str, body: dict, **params) -> Any:
    r = await ctx.http.post(
        f"{META_API_URL}{path}",
        headers=_headers(),
        json=body,
        params={k: v for k, v in params.items() if v is not None},
    )
    r.raise_for_status()
    return r.json()


async def _patch(ctx: Context, path: str, body: dict) -> Any:
    r = await ctx.http.patch(
        f"{META_API_URL}{path}",
        headers=_headers(),
        json=body,
    )
    r.raise_for_status()
    return r.json()


async def _delete(ctx: Context, path: str) -> Any:
    r = await ctx.http.delete(f"{META_API_URL}{path}", headers=_headers())
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {}


# ─── Account ──────────────────────────────────────────────────────────────── #

async def list_ad_accounts(ctx: Context) -> list[dict]:
    """Discover all ad accounts accessible via the server META_ACCESS_TOKEN."""
    try:
        r = await ctx.http.get(f"{META_API_URL}/v1/account", headers=_headers())
        if r.status_code == 200:
            return r.json().get("data", [])
        log.warning("list_ad_accounts: %s %s", r.status_code, r.text[:200])
    except Exception as exc:
        log.error("list_ad_accounts error: %s", exc)
    return []


async def get_account(ctx: Context, ad_account_id: str) -> dict:
    return await _get(ctx, f"/v1/account/{ad_account_id}")


# ─── Campaigns ────────────────────────────────────────────────────────────── #

async def get_campaigns(
    ctx: Context,
    ad_account_id: str,
    status: str = "",
    limit: int = 25,
    after: str = "",
) -> dict:
    return await _get(
        ctx, "/v1/campaigns",
        ad_account_id=ad_account_id,
        status=status or None,
        limit=limit,
        after=after or None,
    )


async def get_campaign(ctx: Context, campaign_id: str) -> dict:
    return await _get(ctx, f"/v1/campaigns/{campaign_id}")


async def create_campaign(ctx: Context, ad_account_id: str, body: dict) -> dict:
    return await _post(ctx, "/v1/campaigns", body, ad_account_id=ad_account_id)


async def update_campaign(ctx: Context, campaign_id: str, body: dict) -> dict:
    return await _patch(ctx, f"/v1/campaigns/{campaign_id}", body)


async def delete_campaign(ctx: Context, campaign_id: str) -> dict:
    return await _delete(ctx, f"/v1/campaigns/{campaign_id}")


# ─── Ad Sets ──────────────────────────────────────────────────────────────── #

async def get_ad_sets(
    ctx: Context,
    ad_account_id: str,
    campaign_id: str = "",
    status: str = "",
    limit: int = 25,
) -> dict:
    return await _get(
        ctx, "/v1/ad-sets",
        ad_account_id=ad_account_id,
        campaign_id=campaign_id or None,
        status=status or None,
        limit=limit,
    )


async def get_ad_set(ctx: Context, ad_set_id: str) -> dict:
    return await _get(ctx, f"/v1/ad-sets/{ad_set_id}")


async def create_ad_set(ctx: Context, ad_account_id: str, body: dict) -> dict:
    return await _post(ctx, "/v1/ad-sets", body, ad_account_id=ad_account_id)


async def update_ad_set(ctx: Context, ad_set_id: str, body: dict) -> dict:
    return await _patch(ctx, f"/v1/ad-sets/{ad_set_id}", body)


async def delete_ad_set(ctx: Context, ad_set_id: str) -> dict:
    return await _delete(ctx, f"/v1/ad-sets/{ad_set_id}")


# ─── Ads ──────────────────────────────────────────────────────────────────── #

async def get_ads(
    ctx: Context,
    ad_account_id: str,
    ad_set_id: str = "",
    status: str = "",
    limit: int = 25,
) -> dict:
    return await _get(
        ctx, "/v1/ads",
        ad_account_id=ad_account_id,
        ad_set_id=ad_set_id or None,
        status=status or None,
        limit=limit,
    )


async def get_ad(ctx: Context, ad_id: str) -> dict:
    return await _get(ctx, f"/v1/ads/{ad_id}")


async def create_ad(ctx: Context, ad_account_id: str, body: dict) -> dict:
    return await _post(ctx, "/v1/ads", body, ad_account_id=ad_account_id)


async def update_ad(ctx: Context, ad_id: str, body: dict) -> dict:
    return await _patch(ctx, f"/v1/ads/{ad_id}", body)


# ─── Creatives ────────────────────────────────────────────────────────────── #

async def get_creatives(ctx: Context, ad_account_id: str, limit: int = 25) -> dict:
    return await _get(ctx, "/v1/creatives", ad_account_id=ad_account_id, limit=limit)


async def get_creative(ctx: Context, creative_id: str) -> dict:
    return await _get(ctx, f"/v1/creatives/{creative_id}")


async def create_creative(ctx: Context, ad_account_id: str, body: dict) -> dict:
    return await _post(ctx, "/v1/creatives", body, ad_account_id=ad_account_id)


# ─── Insights ─────────────────────────────────────────────────────────────── #

async def get_insights(
    ctx: Context,
    level: str,
    ad_account_id: str,
    date_preset: str = "last_7d",
    since: str = "",
    until: str = "",
    fields: str = "",
    limit: int = 25,
) -> dict:
    return await _get(
        ctx, f"/v1/insights/{level}",
        ad_account_id=ad_account_id,
        date_preset=date_preset or None,
        since=since or None,
        until=until or None,
        fields=fields or None,
        limit=limit,
    )


# ─── Audiences ────────────────────────────────────────────────────────────── #

async def get_audiences(ctx: Context, ad_account_id: str, limit: int = 25) -> dict:
    return await _get(ctx, "/v1/audiences", ad_account_id=ad_account_id, limit=limit)


async def get_audience(ctx: Context, audience_id: str) -> dict:
    return await _get(ctx, f"/v1/audiences/{audience_id}")


async def create_audience(ctx: Context, ad_account_id: str, body: dict) -> dict:
    return await _post(ctx, "/v1/audiences", body, ad_account_id=ad_account_id)


async def add_audience_users(
    ctx: Context, audience_id: str, body: dict
) -> dict:
    return await _post(ctx, f"/v1/audiences/{audience_id}/users/add", body)
