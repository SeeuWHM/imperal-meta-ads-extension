"""Meta Ads · Creative management handlers.

Functions: list_creatives, get_creative, create_creative.

Creative flow:
  1. Create creative with image_hash (image must be uploaded via Meta's image endpoint)
     OR use a Page Post creative (link an existing page post as an ad).
  2. Use creative_id in create_ad.

For image upload support, users should upload images via the Meta Business Manager
and provide the image hash, OR the microservice /v1/images endpoint can be used
via raw HTTP (not yet wrapped in this extension — Phase 2 feature).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import meta_providers.meta_client as api


# ─── Models ───────────────────────────────────────────────────────────────── #

class ListCreativesParams(BaseModel):
    limit: int = Field(default=25, description="Max creatives to return")


class CreativeIdParams(BaseModel):
    creative_id: str = Field(description="Creative ID")


class ObjectStorySpec(BaseModel):
    """Defines the content shown in the ad."""
    page_id:     str = Field(description="Facebook Page ID that sponsors the ad")
    link_url:    str = Field(description="Destination URL when user clicks the ad")
    message:     str = Field(description="Primary ad text (up to 125 chars for best performance)")
    headline:    str = Field(default="", description="Ad headline (up to 27 chars)")
    description: str = Field(default="", description="Ad description / link description (optional)")
    image_hash:  str = Field(
        default="",
        description=(
            "Image hash from Meta image library. "
            "Upload images via Meta Business Manager and paste the hash here. "
            "Leave empty to use a link preview image automatically."
        ),
    )
    call_to_action: Literal[
        "LEARN_MORE", "SHOP_NOW", "SIGN_UP", "DOWNLOAD",
        "BOOK_TRAVEL", "CONTACT_US", "GET_OFFER", "SUBSCRIBE",
    ] = Field(default="LEARN_MORE", description="Call-to-action button label")


class CreateCreativeParams(BaseModel):
    name:   str              = Field(description="Creative name (for internal reference)")
    spec:   ObjectStorySpec  = Field(description="Ad content specification")


# ─── list_creatives ───────────────────────────────────────────────────────── #

@chat.function(
    "list_creatives",
    action_type="read",
    description=(
        "List Meta ad creatives in this account. "
        "Creatives define the visual and copy of an ad. "
        "Use creative_id from here when creating ads."
    ),
)
async def fn_list_creatives(ctx, params: ListCreativesParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_creatives(ctx, acc["ad_account_id"], limit=params.limit)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    creatives = data.get("data", [])
    return ActionResult.success(
        data={"creatives": creatives, "total": len(creatives)},
        summary=f"{len(creatives)} creative(s) found.",
    )


# ─── get_creative ─────────────────────────────────────────────────────────── #

@chat.function(
    "get_creative",
    action_type="read",
    description="Get full details for a single Meta creative.",
)
async def fn_get_creative(ctx, params: CreativeIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        creative = await api.get_creative(ctx, params.creative_id)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"creative": creative},
        summary=f"Creative {params.creative_id} loaded.",
    )


# ─── create_creative ──────────────────────────────────────────────────────── #

@chat.function(
    "create_creative",
    action_type="write",
    event="creative.created",
    description=(
        "Create a Meta ad creative (the visual + copy shown in the ad). "
        "Requires a Facebook Page ID and destination URL. "
        "Provide an image_hash for a custom image, or leave empty for auto link preview. "
        "After creating, use the returned creative_id in create_ad."
    ),
)
async def fn_create_creative(ctx, params: CreateCreativeParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    link_data: dict = {
        "link":           params.spec.link_url,
        "message":        params.spec.message,
        "call_to_action": {"type": params.spec.call_to_action},
    }
    if params.spec.headline:
        link_data["name"] = params.spec.headline
    if params.spec.description:
        link_data["description"] = params.spec.description
    if params.spec.image_hash:
        link_data["image_hash"] = params.spec.image_hash

    body = {
        "name": params.name,
        "object_story_spec": {
            "page_id":   params.spec.page_id,
            "link_data": link_data,
        },
    }

    try:
        result = await api.create_creative(ctx, acc["ad_account_id"], body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    creative_id = result.get("id", "")
    return ActionResult.success(
        data={
            "creative_id": creative_id,
            "name":        params.name,
            "link_url":    params.spec.link_url,
            "message":     params.spec.message,
        },
        summary=f"Creative '{params.name}' created (ID: {creative_id}). Use this ID in create_ad.",
    )
