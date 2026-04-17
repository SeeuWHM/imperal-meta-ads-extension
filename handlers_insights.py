"""Meta Ads · Performance insights and AI analysis handlers.

Functions: get_performance, get_budget_status, analyze_performance.

Meta Insights API supports sync (up to ~30 days) and async jobs (90+ days).
This extension uses sync endpoints only (sufficient for most use cases).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import meta_providers.meta_client as api
from meta_providers.helpers import cents_to_dollars


# ─── Helpers ──────────────────────────────────────────────────────────────── #

_PRESET_MAP = {
    "today":      "today",
    "yesterday":  "yesterday",
    "last_7d":    "last_7d",
    "last_30d":   "last_30d",
    "this_month": "this_month",
    "last_month": "last_month",
}

_LEVEL_MAP = {
    "account":  "account",
    "campaign": "campaign",
    "ad_set":   "ad-set",
    "ad":       "ad",
}


def _default_date_preset() -> str:
    return "last_7d"


# ─── Models ───────────────────────────────────────────────────────────────── #

class PerformanceParams(BaseModel):
    level: Literal["account", "campaign", "ad_set", "ad"] = Field(
        default="campaign",
        description=(
            "Report level: account (total), campaign, ad_set, or ad (most granular)"
        ),
    )
    date_preset: Literal[
        "today", "yesterday", "last_7d", "last_30d", "this_month", "last_month"
    ] = Field(
        default="last_7d",
        description="Date range preset",
    )
    fields: str = Field(
        default="",
        description=(
            "Comma-separated fields to include. Leave empty for defaults "
            "(impressions, clicks, spend, cpc, ctr, conversions, roas)."
        ),
    )
    limit: int = Field(default=25, description="Max rows to return")


class AnalyzeParams(BaseModel):
    date_preset: Literal[
        "today", "yesterday", "last_7d", "last_30d", "this_month", "last_month"
    ] = Field(
        default="last_7d",
        description="Date range for analysis",
    )
    focus: Literal[
        "general", "budget", "creatives", "audiences", "conversions", "roas"
    ] = Field(
        default="general",
        description="Analysis focus area",
    )


# ─── get_performance ──────────────────────────────────────────────────────── #

@chat.function(
    "get_performance",
    action_type="read",
    description=(
        "Fetch Meta Ads performance metrics: impressions, clicks, spend, CPC, CTR, "
        "conversions, ROAS. Supports account/campaign/ad_set/ad level breakdown."
    ),
)
async def fn_get_performance(ctx, params: PerformanceParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    level_path = _LEVEL_MAP.get(params.level, "campaign")
    default_fields = (
        "campaign_name,campaign_id,impressions,clicks,spend,cpc,ctr,"
        "conversions,cost_per_conversion,purchase_roas"
    )
    fields = params.fields or default_fields

    try:
        data = await api.get_insights(
            ctx,
            level=level_path,
            ad_account_id=acc["ad_account_id"],
            date_preset=_PRESET_MAP.get(params.date_preset, "last_7d"),
            fields=fields,
            limit=params.limit,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    rows = data.get("data", [])
    return ActionResult.success(
        data={
            "rows":        rows,
            "total":       len(rows),
            "level":       params.level,
            "date_preset": params.date_preset,
            "paging":      data.get("paging", {}),
        },
        summary=f"{len(rows)} row(s) of {params.level} insights ({params.date_preset}).",
    )


# ─── get_budget_status ────────────────────────────────────────────────────── #

@chat.function(
    "get_budget_status",
    action_type="read",
    description=(
        "Show today's spend vs budget for all active campaigns and ad sets. "
        "Highlights campaigns and ad sets nearing their daily budget limit."
    ),
)
async def fn_get_budget_status(ctx) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    try:
        campaigns_data = await api.get_campaigns(
            ctx, acc["ad_account_id"], status="ACTIVE", limit=50
        )
        today_data = await api.get_insights(
            ctx, level="campaign",
            ad_account_id=acc["ad_account_id"],
            date_preset="today",
            fields="campaign_id,campaign_name,spend",
            limit=50,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    campaigns  = campaigns_data.get("data", [])
    today_rows = today_data.get("data", [])

    spend_map = {r.get("campaign_id", ""): float(r.get("spend", 0)) for r in today_rows}

    result = []
    for c in campaigns:
        cid    = c.get("id", "")
        budget = cents_to_dollars(c.get("daily_budget", 0) or c.get("lifetime_budget", 0))
        spend  = spend_map.get(cid, 0.0)
        pct    = round(spend / budget * 100, 1) if budget > 0 else 0.0

        result.append({
            "campaign_id":   cid,
            "campaign_name": c.get("name", ""),
            "status":        c.get("status", ""),
            "daily_budget":  budget,
            "today_spend":   round(spend, 2),
            "pct_used":      pct,
            "alert":         pct >= 90,
        })

    result.sort(key=lambda x: x["pct_used"], reverse=True)
    alerts = [r for r in result if r["alert"]]

    return ActionResult.success(
        data={"campaigns": result, "alerts": alerts, "date": date.today().isoformat()},
        summary=(
            f"Budget status: {len(alerts)} campaign(s) near limit."
            if alerts else
            f"Budget status: {len(result)} campaign(s), all within budget."
        ),
    )


# ─── analyze_performance ──────────────────────────────────────────────────── #

@chat.function(
    "analyze_performance",
    action_type="read",
    description=(
        "AI-powered analysis of Meta Ads performance with actionable recommendations. "
        "Identifies top/underperforming campaigns, budget efficiency, creative insights."
    ),
)
async def fn_analyze_performance(ctx, params: AnalyzeParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    date_preset = _PRESET_MAP.get(params.date_preset, "last_7d")

    await ctx.progress(10, "Fetching campaign performance data…")
    try:
        camp_data = await api.get_insights(
            ctx, level="campaign",
            ad_account_id=acc["ad_account_id"],
            date_preset=date_preset,
            fields=(
                "campaign_name,campaign_id,objective,"
                "impressions,clicks,spend,cpc,ctr,"
                "conversions,cost_per_conversion,purchase_roas"
            ),
            limit=50,
        )
        adset_data = await api.get_insights(
            ctx, level="ad-set",
            ad_account_id=acc["ad_account_id"],
            date_preset=date_preset,
            fields="adset_name,adset_id,impressions,clicks,spend,ctr,conversions",
            limit=25,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    await ctx.progress(60, "Running AI analysis…")

    camp_rows  = camp_data.get("data", [])
    adset_rows = adset_data.get("data", [])[:20]

    prompt = (
        f"Analyse this Meta Ads account performance for period: {params.date_preset}. "
        f"Focus area: {params.focus}.\n\n"
        f"CAMPAIGN DATA:\n{camp_rows!r:.3000}\n\n"
        f"AD SET DATA (top 20):\n{adset_rows!r:.2000}\n\n"
        "Provide:\n"
        "1. Top 3 key insights with specific numbers (what's working, what's not)\n"
        "2. Top 3 actionable recommendations (specific changes with exact values)\n"
        "3. Budget allocation suggestion (which campaigns to scale or cut)\n"
        "4. Creative/audience optimisation hints based on CTR and conversion rates\n"
        "5. ROAS assessment — are campaigns profitable? Benchmarks: ecom 3x+, leads 2x+\n\n"
        "Use actual numbers. Be specific. No generic advice."
    )
    analysis = await ctx.ai.complete(prompt=prompt, model="claude-sonnet")

    await ctx.progress(100, "Analysis complete.")
    return ActionResult.success(
        data={
            "analysis":    analysis.text,
            "date_preset": params.date_preset,
            "focus":       params.focus,
            "campaigns":   camp_rows,
        },
        summary=f"AI analysis complete ({params.date_preset}).",
    )
