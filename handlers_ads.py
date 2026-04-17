"""Meta Ads · Ad management handlers.

Functions: list_ads, get_ad, create_ad, update_ad.

Ads link an ad set to a creative. Creative must exist first.
Creative flow: upload image → create creative → create ad with creative_id.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import meta_providers.meta_client as api


# ─── Models ───────────────────────────────────────────────────────────────── #

class ListAdsParams(BaseModel):
    ad_set_id: str = Field(default="", description="Filter by ad set ID (recommended)")
    status:    Literal["ACTIVE", "PAUSED", ""] = Field(default="", description="Filter by status")
    limit:     int = Field(default=25, description="Max ads to return")


class AdIdParams(BaseModel):
    ad_id: str = Field(description="Ad ID")


class CreateAdParams(BaseModel):
    name:        str  = Field(description="Ad name")
    ad_set_id:   str  = Field(description="Parent ad set ID")
    creative_id: str  = Field(
        description="Creative ID to use (from list_creatives or create_creative)"
    )
    status: Literal["ACTIVE", "PAUSED"] = Field(
        default="PAUSED",
        description="Initial status — use PAUSED to review before activating",
    )


class UpdateAdParams(BaseModel):
    ad_id:       str                             = Field(description="Ad ID to update")
    name:        Optional[str]                   = Field(default=None, description="New ad name")
    status:      Optional[Literal["ACTIVE", "PAUSED"]] = Field(default=None)
    creative_id: Optional[str]                   = Field(
        default=None, description="Replace the creative (swap creative on live ad)"
    )


# ─── list_ads ─────────────────────────────────────────────────────────────── #

@chat.function(
    "list_ads",
    action_type="read",
    description="List Meta ads. Filter by ad_set_id to see ads in a specific ad set.",
)
async def fn_list_ads(ctx, params: ListAdsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_ads(
            ctx, acc["ad_account_id"],
            ad_set_id=params.ad_set_id,
            status=params.status,
            limit=params.limit,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    ads = data.get("data", [])
    return ActionResult.success(
        data={"ads": ads, "total": len(ads)},
        summary=f"{len(ads)} ad(s) found.",
    )


# ─── get_ad ───────────────────────────────────────────────────────────────── #

@chat.function(
    "get_ad",
    action_type="read",
    description="Get full details for a single ad including attached creative.",
)
async def fn_get_ad(ctx, params: AdIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        ad = await api.get_ad(ctx, params.ad_id)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"ad": ad},
        summary=f"Ad {params.ad_id} loaded.",
    )


# ─── create_ad ────────────────────────────────────────────────────────────── #

@chat.function(
    "create_ad",
    action_type="write",
    event="ad.created",
    description=(
        "Create a Meta ad by linking an ad set to a creative. "
        "You MUST have a creative_id first — use list_creatives or create_creative. "
        "Confirm ad_set_id and creative_id with the user before calling."
    ),
)
async def fn_create_ad(ctx, params: CreateAdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body = {
        "name":       params.name,
        "adset_id":   params.ad_set_id,
        "creative":   {"creative_id": params.creative_id},
        "status":     params.status,
    }

    try:
        result = await api.create_ad(ctx, acc["ad_account_id"], body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    ad_id = result.get("id", "")
    return ActionResult.success(
        data={
            "ad_id":       ad_id,
            "name":        params.name,
            "ad_set_id":   params.ad_set_id,
            "creative_id": params.creative_id,
            "status":      params.status,
        },
        summary=f"Ad '{params.name}' created (ID: {ad_id}).",
    )


# ─── update_ad ────────────────────────────────────────────────────────────── #

@chat.function(
    "update_ad",
    action_type="write",
    event="ad.updated",
    description="Update ad name, status, or swap to a different creative.",
)
async def fn_update_ad(ctx, params: UpdateAdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body: dict = {}
    if params.name is not None:
        body["name"] = params.name
    if params.status is not None:
        body["status"] = params.status
    if params.creative_id is not None:
        body["creative"] = {"creative_id": params.creative_id}

    if not body:
        return ActionResult.error("No fields to update provided.", retryable=False)

    try:
        await api.update_ad(ctx, params.ad_id, body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"ad_id": params.ad_id, "updated_fields": list(body.keys())},
        summary=f"Ad {params.ad_id} updated.",
    )
