"""Meta Ads · Custom audience management handlers.

Functions: list_audiences, get_audience, create_audience, add_audience_users.

Custom audiences enable targeting users who have interacted with your business.
All PII must be SHA256-hashed before sending (use hash_pii for assistance).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import meta_providers.meta_client as api


# ─── Models ───────────────────────────────────────────────────────────────── #

class ListAudiencesParams(BaseModel):
    limit: int = Field(default=25, description="Max audiences to return")


class AudienceIdParams(BaseModel):
    audience_id: str = Field(description="Custom audience ID")


class CreateAudienceParams(BaseModel):
    name:           str = Field(description="Audience name")
    description:    str = Field(default="", description="Internal description (optional)")
    subtype: Literal["CUSTOM", "WEBSITE", "APP", "LOOKALIKE", "ENGAGEMENT"] = Field(
        default="CUSTOM",
        description=(
            "Audience type: "
            "CUSTOM (upload customer list), "
            "WEBSITE (website visitors via pixel), "
            "APP (app users), "
            "LOOKALIKE (similar to existing audience), "
            "ENGAGEMENT (page/post engagers)"
        ),
    )
    retention_days: int = Field(
        default=30,
        description="How many days to keep users in the audience (WEBSITE/APP only, 1-180)",
    )
    lookalike_spec: Optional[dict] = Field(
        default=None,
        description=(
            "For LOOKALIKE type: {origin_audience_id, country, ratio (0.01-0.20)} "
            "Example: {origin_audience_id: '123', country: 'US', ratio: 0.05}"
        ),
    )


class AddUsersParams(BaseModel):
    audience_id: str = Field(description="Custom audience ID to add users to")
    schema_type: Literal["EMAIL", "PHONE", "EXTERN_ID"] = Field(
        default="EMAIL",
        description=(
            "Type of identifier: EMAIL (SHA256 hashed), PHONE (SHA256 hashed), "
            "EXTERN_ID (your internal user ID, unhashed)"
        ),
    )
    hashed_data: list[str] = Field(
        description=(
            "List of SHA256-hashed values (lowercase before hashing). "
            "Max 10,000 per request. "
            "For EMAIL: sha256(lowercase(email)). "
            "For PHONE: sha256(digits only, no country code prefix)."
        ),
    )


# ─── list_audiences ───────────────────────────────────────────────────────── #

@chat.function(
    "list_audiences",
    action_type="read",
    description=(
        "List custom audiences in this Meta Ads account. "
        "Shows audience size, type, and status."
    ),
)
async def fn_list_audiences(ctx, params: ListAudiencesParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_audiences(ctx, acc["ad_account_id"], limit=params.limit)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    audiences = data.get("data", [])
    return ActionResult.success(
        data={"audiences": audiences, "total": len(audiences)},
        summary=f"{len(audiences)} audience(s) found.",
    )


# ─── get_audience ─────────────────────────────────────────────────────────── #

@chat.function(
    "get_audience",
    action_type="read",
    description="Get details for a single custom audience including approximate size.",
)
async def fn_get_audience(ctx, params: AudienceIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        audience = await api.get_audience(ctx, params.audience_id)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"audience": audience},
        summary=f"Audience {params.audience_id} loaded.",
    )


# ─── create_audience ──────────────────────────────────────────────────────── #

@chat.function(
    "create_audience",
    action_type="write",
    event="audience.created",
    description=(
        "Create a new Meta custom audience. "
        "For CUSTOM type: create empty audience first, then use add_audience_users. "
        "For LOOKALIKE: requires an existing source audience ID."
    ),
)
async def fn_create_audience(ctx, params: CreateAudienceParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body: dict = {
        "name":    params.name,
        "subtype": params.subtype,
    }
    if params.description:
        body["description"] = params.description
    if params.subtype in ("WEBSITE", "APP"):
        body["retention_days"] = params.retention_days
    if params.subtype == "LOOKALIKE" and params.lookalike_spec:
        body["lookalike_spec"] = params.lookalike_spec

    try:
        result = await api.create_audience(ctx, acc["ad_account_id"], body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    audience_id = result.get("id", "")
    return ActionResult.success(
        data={
            "audience_id": audience_id,
            "name":        params.name,
            "subtype":     params.subtype,
        },
        summary=(
            f"Audience '{params.name}' created (ID: {audience_id}). "
            + ("Use add_audience_users to populate it." if params.subtype == "CUSTOM" else "")
        ),
    )


# ─── add_audience_users ───────────────────────────────────────────────────── #

@chat.function(
    "add_audience_users",
    action_type="write",
    event="audience.updated",
    description=(
        "Add users to a CUSTOM Meta audience by uploading hashed identifiers. "
        "IMPORTANT: All PII must be SHA256-hashed before sending. "
        "Max 10,000 users per call. Batch larger lists into multiple calls."
    ),
)
async def fn_add_audience_users(ctx, params: AddUsersParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    if not params.hashed_data:
        return ActionResult.error("hashed_data cannot be empty.", retryable=False)
    if len(params.hashed_data) > 10_000:
        return ActionResult.error(
            f"Too many users ({len(params.hashed_data)}). Max 10,000 per call. "
            "Split into multiple batches.",
            retryable=False,
        )

    body = {
        "schema": [params.schema_type],
        "data":   [[h] for h in params.hashed_data],
        "is_raw": True,
        "pre_hashed": True,
    }

    try:
        result = await api.add_audience_users(ctx, params.audience_id, body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    num_added   = result.get("num_received", len(params.hashed_data))
    num_invalid = result.get("num_invalid_entries", 0)
    return ActionResult.success(
        data={
            "audience_id": params.audience_id,
            "num_added":   num_added,
            "num_invalid": num_invalid,
            "schema":      params.schema_type,
        },
        summary=(
            f"Added {num_added} user(s) to audience {params.audience_id}."
            + (f" {num_invalid} invalid entries skipped." if num_invalid else "")
        ),
    )
