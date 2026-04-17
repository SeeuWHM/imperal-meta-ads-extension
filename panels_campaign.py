"""Meta Ads · Right panel: campaign detail with ad sets and performance."""
from __future__ import annotations

import asyncio

from imperal_sdk import ui

from app import ext, _get_ready_account
import meta_providers.meta_client as api
from meta_providers.helpers import SECTION, cents_to_dollars
from panels_ui import (
    campaign_badge, short_objective,
    fmt_currency, fmt_pct, fmt_number,
)

_BID_SHORT = {
    "LOWEST_COST_WITHOUT_CAP":   "Lowest Cost",
    "LOWEST_COST_WITH_BID_CAP":  "Bid Cap",
    "COST_CAP":                  "Cost Cap",
    "LOWEST_COST_WITH_MIN_ROAS": "Min ROAS",
}


@ext.panel("campaign_detail", slot="right", title="Campaign")
async def panel_campaign_detail(
    ctx,
    campaign_id: str = "",
    **kwargs,
) -> ui.UINode:
    """Campaign detail: settings header + today's perf chart + ad sets list."""
    if not campaign_id:
        return ui.Stack([
            ui.Empty(
                message="Select a campaign from the left panel.",
                icon="MousePointer",
            ),
        ])

    acc, err = await _get_ready_account(ctx)
    if err:
        return ui.Stack([ui.Alert(type="error", message=err.message)])

    # ── Parallel fetch: campaign details + skeleton ────────────────────────── #
    try:
        camp_data, ad_sets_data, skel = await asyncio.gather(
            api.get_campaign(ctx, campaign_id),
            api.get_ad_sets(ctx, acc["ad_account_id"], campaign_id=campaign_id),
            ctx.skeleton.get(SECTION),
        )
    except Exception as exc:
        return ui.Stack([
            ui.Error(
                message=str(exc)[:200],
                retry=ui.Call("__panel__campaign_detail", campaign_id=campaign_id),
            ),
        ])

    skel      = skel or {}
    campaign  = camp_data if isinstance(camp_data, dict) else {}
    ad_sets   = ad_sets_data.get("data", []) if isinstance(ad_sets_data, dict) else []
    currency  = skel.get("currency", acc.get("currency", "USD"))

    camp_name = campaign.get("name", campaign_id)
    status    = campaign.get("status", "")
    objective = campaign.get("objective", "")
    bid_str   = campaign.get("bid_strategy", "")
    is_active = status == "ACTIVE"

    budget_cents = campaign.get("daily_budget") or campaign.get("lifetime_budget") or 0
    budget       = cents_to_dollars(budget_cents) if budget_cents else 0.0

    # Find this campaign's today data in skeleton
    all_camps  = skel.get("campaigns", [])
    camp_skel  = next(
        (c for c in all_camps if str(c.get("id", "")) == str(campaign_id)), {}
    )
    today_spend  = float(camp_skel.get("spend_today", 0) or 0)
    today_clicks = int(  camp_skel.get("clicks_today", 0) or 0)
    today_ctr    = float(camp_skel.get("ctr", 0) or 0)
    today_conv   = float(camp_skel.get("conversions", 0) or 0)

    # ── Header ────────────────────────────────────────────────────────────── #
    header = ui.Stack([
        ui.Stack([
            ui.Text(content=camp_name, variant="heading"),
            campaign_badge(status),
        ], direction="h", gap=2),
        ui.Text(
            content=f"ID: {campaign_id}",
            variant="caption",
        ),
    ])

    # ── Key settings ──────────────────────────────────────────────────────── #
    settings_stats = ui.Stats(columns=3, children=[
        ui.Stat(label="Daily Budget", value=fmt_currency(budget, currency) if budget else "Ad Set",
                icon="DollarSign"),
        ui.Stat(label="Objective",    value=short_objective(objective),
                icon="Target"),
        ui.Stat(label="Bid Strategy", value=_BID_SHORT.get(bid_str, bid_str[:12] if bid_str else "—"),
                icon="TrendingUp"),
    ])

    # ── Tabs ──────────────────────────────────────────────────────────────── #
    perf_tab = _build_perf_tab(
        budget, today_spend, today_clicks, today_ctr, today_conv, today_roas,
        currency, campaign_id, camp_name,
    )
    adsets_tab = _build_adsets_tab(ad_sets, currency, camp_name)

    tabs = ui.Tabs(tabs=[
        {"label": "Today",                    "content": [perf_tab]},
        {"label": f"Ad Sets ({len(ad_sets)})", "content": [adsets_tab]},
    ], default_tab=0)

    # ── Sticky footer ──────────────────────────────────────────────────────── #
    footer = ui.Stack([
        ui.Button(
            label="Pause" if is_active else "Resume",
            icon="Pause" if is_active else "Play",
            variant="ghost",
            on_click=ui.Call(
                "pause_campaign" if is_active else "resume_campaign",
                campaign_id=campaign_id,
            ),
        ),
        ui.Button(label="7-day report", icon="BarChart2", variant="ghost",
                  on_click=ui.Send(f"Show 7-day performance for campaign '{camp_name}'")),
        ui.Button(label="AI Analyse", icon="Sparkles", variant="ghost",
                  on_click=ui.Send(f"Analyse performance of Meta Ads campaign '{camp_name}'")),
    ], direction="horizontal", gap=2, sticky=True)

    return ui.Stack([header, ui.Divider(), settings_stats, ui.Divider(), tabs, footer])


# ─── Today's performance tab ──────────────────────────────────────────────── #

def _build_perf_tab(
    budget: float, spend: float, clicks: int, ctr: float,
    conversions: float, roas: float,
    currency: str, campaign_id: str, camp_name: str,
) -> ui.UINode:
    chart_data = [
        {"metric": "Spent Today", "amount": round(spend, 2)},
        {"metric": "Daily Budget", "amount": round(budget, 2)},
    ]

    pct = round(spend / budget * 100, 1) if budget else 0

    alert_node: list = []
    if pct >= 90:
        alert_node = [ui.Alert(type="error",  message=f"Budget critical — {pct:.0f}% used")]
    elif pct >= 70:
        alert_node = [ui.Alert(type="warn",   message=f"Budget warning — {pct:.0f}% used")]

    today_kpis = ui.Stats(columns=2, children=[
        ui.Stat(label="Spend Today",  value=fmt_currency(spend, currency),
                icon="DollarSign",   color="blue"),
        ui.Stat(label="Clicks",       value=fmt_number(clicks),
                icon="MousePointer", color="green"),
        ui.Stat(label="CTR",          value=fmt_pct(ctr),
                icon="Percent"),
        ui.Stat(label="Conversions",  value=fmt_number(int(conversions)),
                icon="CheckCircle",  color="purple"),
    ])

    return ui.Stack([
        *alert_node,
        ui.Text(content="Spend vs Daily Budget", variant="label"),
        ui.Chart(data=chart_data, type="bar", x_key="metric", height=130),
        ui.Divider(label="TODAY'S METRICS"),
        today_kpis,
    ])


# ─── Ad Sets tab ──────────────────────────────────────────────────────────── #

def _build_adsets_tab(
    ad_sets: list, currency: str, camp_name: str,
) -> ui.UINode:
    if not ad_sets:
        return ui.Stack([
            ui.Empty(
                message="No ad sets yet.",
                icon="Layers",
                action=ui.Send(f"Create an ad set in Meta campaign '{camp_name}'"),
            ),
        ])

    items = []
    for ads in ad_sets:
        adset_id     = str(ads.get("id", ""))
        adset_name   = ads.get("name", "")
        adset_status = ads.get("status", "")
        budget       = cents_to_dollars(ads.get("daily_budget") or ads.get("lifetime_budget") or 0)
        is_active    = adset_status == "ACTIVE"

        items.append(ui.ListItem(
            id=adset_id,
            title=adset_name,
            subtitle=fmt_currency(budget, currency) + "/day" if budget else "Inherited budget",
            icon="Layers",
            badge=campaign_badge(adset_status),
            actions=[
                {
                    "icon":     "Pause" if is_active else "Play",
                    "label":    "Pause" if is_active else "Resume",
                    "on_click": ui.Call(
                        "pause_ad_set" if is_active else "resume_ad_set",
                        ad_set_id=adset_id,
                    ),
                },
                {
                    "icon":     "Eye",
                    "label":    "View Ads",
                    "on_click": ui.Send(f"Show ads in ad set '{adset_name}'"),
                },
            ],
        ))

    return ui.Stack([
        ui.List(items=items, searchable=True),
        ui.Button(label="+ Ad Set", icon="Plus", variant="ghost",
                  on_click=ui.Send(f"Create an ad set in Meta campaign '{camp_name}'")),
    ])
