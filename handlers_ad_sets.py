"""Meta Ads · Ad Set management handlers.

Functions: list_ad_sets, get_ad_set, create_ad_set,
           update_ad_set, pause_ad_set, resume_ad_set.

Ad Sets hold the targeting, placement, budget, and schedule.
Budgets are in USD (converted to cents for the API).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import meta_providers.meta_client as api
from meta_providers.helpers import dollars_to_cents


# ─── Models ───────────────────────────────────────────────────────────────── #

class ListAdSetsParams(BaseModel):
    campaign_id: str = Field(default="", description="Filter by campaign ID (recommended)")
    status:      Literal["ACTIVE", "PAUSED", ""] = Field(
        default="", description="Filter by status"
    )
    limit: int = Field(default=25, description="Max ad sets to return")


class AdSetIdParams(BaseModel):
    ad_set_id: str = Field(description="Ad Set ID")


class GeoLocationModel(BaseModel):
    countries: list[str] = Field(
        default=["US"],
        description="List of 2-letter country codes, e.g. ['US', 'CA', 'GB']",
    )


class TargetingModel(BaseModel):
    geo_locations: GeoLocationModel = Field(
        default_factory=GeoLocationModel,
        description="Geographic targeting",
    )
    age_min: int = Field(default=18, description="Minimum age (18-65)")
    age_max: int = Field(default=65, description="Maximum age (18-65)")
    genders: list[int] = Field(
        default=[],
        description="Gender targeting: 1=male, 2=female, [] for all",
    )


class CreateAdSetParams(BaseModel):
    name:             str            = Field(description="Ad Set name")
    campaign_id:      str            = Field(description="Parent campaign ID")
    daily_budget_usd: float          = Field(
        description="Daily budget in USD (e.g. 50.00 for $50/day)"
    )
    destination_type: Literal["WEBSITE", "APP", "INSTAGRAM_PROFILE", "MESSENGER", "WHATSAPP"] = Field(
        default="WEBSITE",
        description="Destination: WEBSITE (URL), APP (app store), or social profile",
    )
    targeting:        TargetingModel = Field(
        default_factory=TargetingModel,
        description="Audience targeting: geo, age, gender",
    )
    bid_amount_usd: Optional[float] = Field(
        default=None,
        description="Manual bid amount in USD (only for LOWEST_COST_WITH_BID_CAP campaigns)",
    )
    optimization_goal: Literal[
        "LINK_CLICKS", "IMPRESSIONS", "REACH", "LEAD_GENERATION",
        "CONVERSIONS", "APP_INSTALLS", "VIDEO_VIEWS",
    ] = Field(
        default="LINK_CLICKS",
        description="What Meta optimises for within the ad set",
    )


class UpdateAdSetParams(BaseModel):
    ad_set_id:        str              = Field(description="Ad Set ID to update")
    name:             Optional[str]    = Field(default=None, description="New name")
    status:           Optional[Literal["ACTIVE", "PAUSED"]] = Field(default=None)
    daily_budget_usd: Optional[float]  = Field(
        default=None, description="New daily budget in USD"
    )


# ─── list_ad_sets ─────────────────────────────────────────────────────────── #

@chat.function(
    "list_ad_sets",
    action_type="read",
    description="List Meta ad sets. Filter by campaign_id to see ad sets for a specific campaign.",
)
async def fn_list_ad_sets(ctx, params: ListAdSetsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_ad_sets(
            ctx, acc["ad_account_id"],
            campaign_id=params.campaign_id,
            status=params.status,
            limit=params.limit,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    ad_sets = data.get("data", [])
    return ActionResult.success(
        data={"ad_sets": ad_sets, "total": len(ad_sets)},
        summary=f"{len(ad_sets)} ad set(s) found.",
    )


# ─── get_ad_set ───────────────────────────────────────────────────────────── #

@chat.function(
    "get_ad_set",
    action_type="read",
    description="Get full details for a single ad set including targeting specification.",
)
async def fn_get_ad_set(ctx, params: AdSetIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        ad_set = await api.get_ad_set(ctx, params.ad_set_id)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"ad_set": ad_set},
        summary=f"Ad Set {params.ad_set_id} loaded.",
    )


# ─── create_ad_set ────────────────────────────────────────────────────────── #

@chat.function(
    "create_ad_set",
    action_type="write",
    event="ad_set.created",
    description=(
        "Create a Meta ad set inside a campaign. "
        "ALWAYS confirm campaign_id, daily budget, and targeting before calling. "
        "Ad set starts PAUSED — activate after adding creatives and ads."
    ),
)
async def fn_create_ad_set(ctx, params: CreateAdSetParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body: dict = {
        "name":              params.name,
        "campaign_id":       params.campaign_id,
        "daily_budget":      dollars_to_cents(params.daily_budget_usd),
        "destination_type":  params.destination_type,
        "optimization_goal": params.optimization_goal,
        "billing_event":     "IMPRESSIONS",
        "targeting": {
            "geo_locations": {"countries": params.targeting.geo_locations.countries},
            "age_min":       params.targeting.age_min,
            "age_max":       params.targeting.age_max,
        },
        "status": "PAUSED",
    }
    if params.targeting.genders:
        body["targeting"]["genders"] = params.targeting.genders
    if params.bid_amount_usd is not None:
        body["bid_amount"] = dollars_to_cents(params.bid_amount_usd)

    try:
        result = await api.create_ad_set(ctx, acc["ad_account_id"], body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    ad_set_id = result.get("id", "")
    return ActionResult.success(
        data={
            "ad_set_id":        ad_set_id,
            "name":             params.name,
            "campaign_id":      params.campaign_id,
            "daily_budget_usd": params.daily_budget_usd,
            "status":           "PAUSED",
        },
        summary=f"Ad Set '{params.name}' created (ID: {ad_set_id}). Status: PAUSED.",
    )


# ─── update_ad_set ────────────────────────────────────────────────────────── #

@chat.function(
    "update_ad_set",
    action_type="write",
    event="ad_set.updated",
    description="Update ad set name, status, or daily budget. Only provided fields change.",
)
async def fn_update_ad_set(ctx, params: UpdateAdSetParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body: dict = {}
    if params.name is not None:
        body["name"] = params.name
    if params.status is not None:
        body["status"] = params.status
    if params.daily_budget_usd is not None:
        body["daily_budget"] = dollars_to_cents(params.daily_budget_usd)

    if not body:
        return ActionResult.error("No fields to update provided.", retryable=False)

    try:
        await api.update_ad_set(ctx, params.ad_set_id, body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"ad_set_id": params.ad_set_id, "updated_fields": list(body.keys())},
        summary=f"Ad Set {params.ad_set_id} updated.",
    )


# ─── pause_ad_set / resume_ad_set ─────────────────────────────────────────── #

@chat.function(
    "pause_ad_set",
    action_type="write",
    event="ad_set.paused",
    description="Pause an active Meta ad set.",
)
async def fn_pause_ad_set(ctx, params: AdSetIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        await api.update_ad_set(ctx, params.ad_set_id, {"status": "PAUSED"})
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    return ActionResult.success(
        data={"ad_set_id": params.ad_set_id, "status": "PAUSED"},
        summary=f"Ad Set {params.ad_set_id} paused.",
    )


@chat.function(
    "resume_ad_set",
    action_type="write",
    event="ad_set.resumed",
    description="Resume a paused Meta ad set.",
)
async def fn_resume_ad_set(ctx, params: AdSetIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        await api.update_ad_set(ctx, params.ad_set_id, {"status": "ACTIVE"})
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    return ActionResult.success(
        data={"ad_set_id": params.ad_set_id, "status": "ACTIVE"},
        summary=f"Ad Set {params.ad_set_id} resumed.",
    )
