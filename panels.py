"""Meta Ads · Left panel: account dashboard.

Shows today's KPIs, budget progress, and campaign list from skeleton cache.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from meta_providers.helpers import _all_accounts, SECTION
from panels_ui import (
    campaign_badge,
    fmt_currency, fmt_pct, fmt_number,
    not_connected_view, needs_setup_view, error_view,
)


@ext.panel("account_dashboard", slot="left", title="Meta Ads", icon="Target")
async def panel_account_dashboard(ctx, **kwargs) -> ui.UINode:
    """Account KPIs, budget bar, and campaigns list — served from skeleton cache."""
    data = await ctx.skeleton.get(SECTION) or {}

    # ── Connection states ─────────────────────────────────────────────────── #
    if not data.get("connected"):
        accounts = await _all_accounts(ctx)
        if not accounts:
            return not_connected_view()
        if any(a.get("_needs_setup") for a in accounts):
            return needs_setup_view()
        return error_view("Connection error. Try reconnecting.")

    # ── Extract skeleton data ──────────────────────────────────────────────── #
    today     = data.get("today", {})
    campaigns = data.get("campaigns", [])
    alerts    = data.get("alerts", [])
    currency  = data.get("currency", "USD")

    spend       = float(today.get("spend", 0) or 0)
    clicks      = int(  today.get("clicks", 0) or 0)
    impressions = int(  today.get("impressions", 0) or 0)
    ctr         = float(today.get("ctr", 0) or 0)
    conversions = float(today.get("conversions", 0) or 0)

    budget_total = sum(float(c.get("budget", 0) or 0) for c in campaigns)
    pct_spent    = round(spend / budget_total * 100, 1) if budget_total else 0

    n_active = sum(1 for c in campaigns if c.get("status") == "ACTIVE")
    n_paused = sum(1 for c in campaigns if c.get("status") == "PAUSED")

    # ── Budget progress bar ────────────────────────────────────────────────── #
    budget_bar = ui.Progress(
        value=min(int(pct_spent), 100),
        label=(
            f"{fmt_currency(spend, currency)} / {fmt_currency(budget_total, currency)} "
            f"today · {pct_spent:.0f}%"
        ),
    )

    # ── Budget alerts (max 2) ──────────────────────────────────────────────── #
    alert_nodes = [
        ui.Alert(
            type="error",
            message=f"{a.get('campaign_name', 'Campaign')}: {a.get('pct_used', 0):.0f}% budget used",
        )
        for a in alerts[:2]
    ]

    # ── Today's KPI stats ──────────────────────────────────────────────────── #
    kpi_stats = ui.Stats(columns=2, children=[
        ui.Stat(label="Spend Today",  value=fmt_currency(spend, currency),
                icon="DollarSign",   color="blue"),
        ui.Stat(label="Clicks",       value=fmt_number(clicks),
                icon="MousePointer", color="green"),
        ui.Stat(label="Impressions",  value=fmt_number(impressions),
                icon="Eye"),
        ui.Stat(label="CTR",          value=fmt_pct(ctr),
                icon="Percent"),
    ])

    # ── Campaigns list ─────────────────────────────────────────────────────── #
    camp_items = []
    for c in campaigns:
        cid       = str(c.get("id", ""))
        c_spend   = float(c.get("spend_today", 0) or 0)
        c_clicks  = int(c.get("clicks_today", 0) or 0)
        c_status  = c.get("status", "")
        c_obj     = c.get("objective", "")
        is_active = c_status == "ACTIVE"

        camp_items.append(ui.ListItem(
            id=cid,
            title=c.get("name", "Campaign"),
            subtitle=f"{fmt_currency(c_spend, currency)} · {fmt_number(c_clicks)} clicks",
            badge=campaign_badge(c_status),
            icon="Play" if is_active else "Pause",
            on_click=ui.Call("__panel__campaign_detail", campaign_id=cid),
            actions=[{
                "icon":     "Pause" if is_active else "Play",
                "label":    "Pause" if is_active else "Resume",
                "on_click": ui.Call(
                    "pause_campaign" if is_active else "resume_campaign",
                    campaign_id=cid,
                ),
            }],
        ))

    camp_divider = ui.Divider(
        label=f"CAMPAIGNS  ·  {n_active} active  {n_paused} paused"
              if (n_active or n_paused) else f"CAMPAIGNS ({len(campaigns)})"
    )

    camp_list = (
        ui.List(items=camp_items, searchable=True, page_size=10)
        if camp_items else
        ui.Empty(
            message="No active campaigns.",
            icon="BarChart2",
            action=ui.Send("Create a new Meta Ads campaign"),
        )
    )

    # ── Sticky footer ──────────────────────────────────────────────────────── #
    footer = ui.Stack([
        ui.Button(label="+ Campaign", variant="primary", icon="Plus",
                  on_click=ui.Send("Create a new Meta Ads campaign")),
        ui.Button(label="", icon="RefreshCw", variant="ghost", size="sm",
                  on_click=ui.Call("__panel__account_dashboard")),
    ], direction="horizontal", gap=2, sticky=True)

    return ui.Stack([
        ui.Header(
            text=data.get("account_name", "Meta Ads"),
            subtitle=f"ID: {data.get('ad_account_id', '')}",
        ),
        budget_bar,
        *alert_nodes,
        kpi_stats,
        camp_divider,
        camp_list,
        footer,
    ])
