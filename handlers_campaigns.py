"""Meta Ads · Campaign management handlers.

Functions: list_campaigns, get_campaign, create_campaign,
           update_campaign, pause_campaign, resume_campaign.

Meta campaigns set the objective and bid strategy.
Budgets are typically at the ad set level (CBO off by default).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import meta_providers.meta_client as api
from meta_providers.helpers import dollars_to_cents, cents_to_dollars


# ─── Models ───────────────────────────────────────────────────────────────── #

class ListCampaignsParams(BaseModel):
    status: Literal["ACTIVE", "PAUSED", ""] = Field(
        default="",
        description="Filter by status: ACTIVE, PAUSED, or empty for all",
    )
    limit: int = Field(default=25, description="Max campaigns to return (1-100)")


class CampaignIdParams(BaseModel):
    campaign_id: str = Field(description="Campaign ID (numeric string)")


class CreateCampaignParams(BaseModel):
    name:      str   = Field(description="Campaign name (unique within account)")
    objective: Literal[
        "OUTCOME_TRAFFIC", "OUTCOME_LEADS", "OUTCOME_SALES",
        "OUTCOME_AWARENESS", "OUTCOME_ENGAGEMENT", "OUTCOME_APP_PROMOTION",
    ] = Field(
        default="OUTCOME_TRAFFIC",
        description=(
            "Campaign objective: OUTCOME_TRAFFIC (website visits), "
            "OUTCOME_LEADS (lead gen forms), OUTCOME_SALES (conversions/ROAS), "
            "OUTCOME_AWARENESS (reach/brand), OUTCOME_ENGAGEMENT (post/page engagement), "
            "OUTCOME_APP_PROMOTION (app installs)"
        ),
    )
    bid_strategy: Literal[
        "LOWEST_COST_WITHOUT_CAP", "LOWEST_COST_WITH_BID_CAP",
        "COST_CAP", "LOWEST_COST_WITH_MIN_ROAS",
    ] = Field(
        default="LOWEST_COST_WITHOUT_CAP",
        description=(
            "Bid strategy: LOWEST_COST_WITHOUT_CAP (auto, recommended for most), "
            "LOWEST_COST_WITH_BID_CAP (manual max bid), "
            "COST_CAP (target cost per result), "
            "LOWEST_COST_WITH_MIN_ROAS (minimum ROAS target)"
        ),
    )
    daily_budget_usd: Optional[float] = Field(
        default=None,
        description=(
            "Campaign-level daily budget in USD (enables Campaign Budget Optimisation). "
            "Leave empty to set budget at ad set level instead (recommended for precise control)."
        ),
    )


class UpdateCampaignParams(BaseModel):
    campaign_id:      str                    = Field(description="Campaign ID to update")
    name:             Optional[str]          = Field(default=None, description="New campaign name")
    status:           Optional[Literal["ACTIVE", "PAUSED"]] = Field(
        default=None, description="New status"
    )
    daily_budget_usd: Optional[float]        = Field(
        default=None, description="New daily budget in USD (CBO campaigns only)"
    )
    bid_strategy:     Optional[Literal[
        "LOWEST_COST_WITHOUT_CAP", "LOWEST_COST_WITH_BID_CAP",
        "COST_CAP", "LOWEST_COST_WITH_MIN_ROAS",
    ]] = Field(default=None, description="New bid strategy")


# ─── list_campaigns ───────────────────────────────────────────────────────── #

@chat.function(
    "list_campaigns",
    action_type="read",
    description="List Meta Ads campaigns with status, objective, and today's performance.",
)
async def fn_list_campaigns(ctx, params: ListCampaignsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_campaigns(
            ctx, acc["ad_account_id"],
            status=params.status, limit=params.limit,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    campaigns = data.get("data", [])
    return ActionResult.success(
        data={"campaigns": campaigns, "total": len(campaigns), "filter": params.status or "all"},
        summary=f"{len(campaigns)} campaign(s) found.",
    )


# ─── get_campaign ─────────────────────────────────────────────────────────── #

@chat.function(
    "get_campaign",
    action_type="read",
    description="Get full details for a single Meta campaign.",
)
async def fn_get_campaign(ctx, params: CampaignIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        campaign = await api.get_campaign(ctx, params.campaign_id)
        ad_sets  = await api.get_ad_sets(
            ctx, acc["ad_account_id"], campaign_id=params.campaign_id
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={
            "campaign":    campaign,
            "ad_sets":     ad_sets.get("data", []),
            "campaign_id": params.campaign_id,
        },
        summary="Campaign details loaded.",
    )


# ─── create_campaign ──────────────────────────────────────────────────────── #

@chat.function(
    "create_campaign",
    action_type="write",
    event="campaign.created",
    description=(
        "Create a new Meta Ads campaign. "
        "ALWAYS ask the user for name and objective before calling. "
        "Campaign starts PAUSED — activate it after adding ad sets and creatives."
    ),
)
async def fn_create_campaign(ctx, params: CreateCampaignParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body: dict = {
        "name":         params.name,
        "objective":    params.objective,
        "bid_strategy": params.bid_strategy,
        "status":       "PAUSED",
    }
    if params.daily_budget_usd is not None:
        body["daily_budget"] = dollars_to_cents(params.daily_budget_usd)

    try:
        result = await api.create_campaign(ctx, acc["ad_account_id"], body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    campaign_id = result.get("id", "")
    return ActionResult.success(
        data={
            "campaign_id":  campaign_id,
            "name":         params.name,
            "objective":    params.objective,
            "bid_strategy": params.bid_strategy,
            "status":       "PAUSED",
        },
        summary=f"Campaign '{params.name}' created (ID: {campaign_id}). Status: PAUSED.",
    )


# ─── update_campaign ──────────────────────────────────────────────────────── #

@chat.function(
    "update_campaign",
    action_type="write",
    event="campaign.updated",
    description="Update campaign name, status, budget, or bid strategy. Only provided fields change.",
)
async def fn_update_campaign(ctx, params: UpdateCampaignParams) -> ActionResult:
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
    if params.bid_strategy is not None:
        body["bid_strategy"] = params.bid_strategy

    if not body:
        return ActionResult.error("No fields to update provided.", retryable=False)

    try:
        await api.update_campaign(ctx, params.campaign_id, body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"campaign_id": params.campaign_id, "updated_fields": list(body.keys())},
        summary=f"Campaign {params.campaign_id} updated.",
    )


# ─── pause_campaign ───────────────────────────────────────────────────────── #

@chat.function(
    "pause_campaign",
    action_type="write",
    event="campaign.paused",
    description="Pause an active Meta campaign. Stops all ad delivery immediately.",
)
async def fn_pause_campaign(ctx, params: CampaignIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        await api.update_campaign(ctx, params.campaign_id, {"status": "PAUSED"})
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    return ActionResult.success(
        data={"campaign_id": params.campaign_id, "status": "PAUSED"},
        summary=f"Campaign {params.campaign_id} paused.",
    )


# ─── resume_campaign ──────────────────────────────────────────────────────── #

@chat.function(
    "resume_campaign",
    action_type="write",
    event="campaign.resumed",
    description="Resume a paused Meta campaign.",
)
async def fn_resume_campaign(ctx, params: CampaignIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        await api.update_campaign(ctx, params.campaign_id, {"status": "ACTIVE"})
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    return ActionResult.success(
        data={"campaign_id": params.campaign_id, "status": "ACTIVE"},
        summary=f"Campaign {params.campaign_id} resumed.",
    )
