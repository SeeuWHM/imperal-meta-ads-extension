"""Meta Ads · Skeleton background tools.

skeleton_refresh_meta_ads: refreshes today's KPIs + campaign list.
skeleton_alert_meta_ads:   sends proactive notification if budget is critical.
"""
from __future__ import annotations

import logging

from app import ext
from meta_providers.helpers import _active_account, SECTION, cents_to_dollars
import meta_providers.meta_client as api

log = logging.getLogger("meta-ads.skeleton")

_BUDGET_ALERT_THRESHOLD = 0.90


@ext.tool(
    "skeleton_refresh_meta_ads",
    description="Background refresh: today's Meta Ads KPIs, campaign list, budget alerts.",
)
async def skeleton_refresh(ctx, **kwargs) -> dict:
    acc = await _active_account(ctx)
    if not acc or not acc.get("ad_account_id") or acc.get("_needs_setup"):
        return {"response": {"connected": False}}

    try:
        campaigns_data = await api.get_campaigns(
            ctx, acc["ad_account_id"], status="ACTIVE", limit=25
        )
        today_data = await api.get_insights(
            ctx, level="campaign",
            ad_account_id=acc["ad_account_id"],
            date_preset="today",
            fields=(
                "campaign_id,campaign_name,impressions,clicks,spend,"
                "ctr,cpc,conversions,purchase_roas"
            ),
            limit=25,
        )
    except Exception as exc:
        log.warning("skeleton_refresh_meta_ads failed: %s", exc)
        return {"response": {"connected": True, "error": str(exc)[:150]}}

    campaigns  = campaigns_data.get("data", [])
    today_rows = {r.get("campaign_id", ""): r for r in today_data.get("data", [])}

    campaign_summaries = []
    alerts             = []

    for camp in campaigns:
        cid    = camp.get("id", "")
        perf   = today_rows.get(cid, {})
        spend  = float(perf.get("spend", 0) or 0)
        budget = cents_to_dollars(camp.get("daily_budget", 0) or 0)

        budget_pct = round(spend / budget, 3) if budget > 0 else 0.0
        if budget_pct >= _BUDGET_ALERT_THRESHOLD and budget > 0:
            alerts.append({
                "type":          "budget_critical",
                "campaign_id":   cid,
                "campaign_name": camp.get("name", cid),
                "spend":         spend,
                "budget":        budget,
                "pct_used":      round(budget_pct * 100, 1),
            })

        campaign_summaries.append({
            "id":            cid,
            "name":          camp.get("name", ""),
            "status":        camp.get("status", ""),
            "objective":     camp.get("objective", ""),
            "budget":        budget,
            "spend_today":   spend,
            "clicks_today":  int(perf.get("clicks", 0) or 0),
            "impressions":   int(perf.get("impressions", 0) or 0),
            "ctr":           float(perf.get("ctr", 0) or 0),
            "conversions":   float(perf.get("conversions", 0) or 0),
            "roas":          float((perf.get("purchase_roas") or [{}])[0].get("value", 0) if isinstance(perf.get("purchase_roas"), list) else perf.get("purchase_roas") or 0),
            "budget_pct":    round(budget_pct * 100, 1),
        })

    # Account-level totals
    total_spend       = sum(float(r.get("spend", 0) or 0) for r in today_rows.values())
    total_clicks      = sum(int(r.get("clicks", 0) or 0) for r in today_rows.values())
    total_impressions = sum(int(r.get("impressions", 0) or 0) for r in today_rows.values())
    total_conversions = sum(float(r.get("conversions", 0) or 0) for r in today_rows.values())
    avg_ctr = round(total_clicks / total_impressions, 4) if total_impressions > 0 else 0.0

    return {"response": {
        "connected":    True,
        "account_name": acc.get("account_name", ""),
        "ad_account_id": acc.get("ad_account_id", ""),
        "currency":     acc.get("currency", "USD"),
        "today": {
            "spend":       round(total_spend, 2),
            "clicks":      total_clicks,
            "impressions": total_impressions,
            "conversions": round(total_conversions, 2),
            "ctr":         avg_ctr,
        },
        "campaigns": campaign_summaries,
        "alerts":    alerts,
    }}


@ext.tool(
    "skeleton_alert_meta_ads",
    description="Proactive alert: notify user when any Meta campaign budget is ≥90% depleted.",
)
async def skeleton_alert(ctx, **kwargs) -> dict:
    data = await ctx.skeleton.get(SECTION) or {}
    if not data.get("connected"):
        return {"response": {}}

    critical = [a for a in data.get("alerts", []) if a.get("type") == "budget_critical"]
    if not critical:
        return {"response": {"alerts_sent": 0}}

    if len(critical) == 1:
        a = critical[0]
        msg = (
            f"Meta Ads budget alert: '{a['campaign_name']}' "
            f"has used {a['pct_used']}% of its daily budget "
            f"(${a['spend']:.2f} / ${a['budget']:.2f})."
        )
    else:
        names = ", ".join(f"'{a['campaign_name']}'" for a in critical[:3])
        msg = f"Meta Ads: {len(critical)} campaigns near daily budget limit: {names}."

    await ctx.notify(msg)
    return {"response": {"alerts_sent": len(critical)}}
