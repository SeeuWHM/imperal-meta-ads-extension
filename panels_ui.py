"""Meta Ads · Shared panel UI helpers."""
from __future__ import annotations

from imperal_sdk import ui

# ─── Formatters ───────────────────────────────────────────────────────────── #

def fmt_currency(amount, currency: str = "USD") -> str:
    symbol = "$" if currency in ("USD", "CAD", "AUD") else currency + " "
    try:
        return f"{symbol}{float(amount):.2f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"


def fmt_pct(value, decimals: int = 2) -> str:
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "0.00%"


def fmt_number(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def fmt_roas(value) -> str:
    try:
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return "—"


# ─── Badge helpers ────────────────────────────────────────────────────────── #

_STATUS_COLORS = {
    "ACTIVE":  "green",
    "PAUSED":  "gray",
    "DELETED": "red",
    "DRAFT":   "yellow",
    "PENDING": "yellow",
}

_OBJECTIVE_SHORT = {
    "OUTCOME_TRAFFIC":        "Traffic",
    "OUTCOME_LEADS":          "Leads",
    "OUTCOME_SALES":          "Sales",
    "OUTCOME_AWARENESS":      "Awareness",
    "OUTCOME_ENGAGEMENT":     "Engagement",
    "OUTCOME_APP_PROMOTION":  "App",
}


def campaign_badge(status: str) -> ui.Badge:
    return ui.Badge(label=status or "—", color=_STATUS_COLORS.get(status, "gray"))


def short_objective(objective: str) -> str:
    """Return short display string for a Meta campaign objective."""
    return _OBJECTIVE_SHORT.get(objective, objective[:12] if objective else "—")


# ─── Connection state views ───────────────────────────────────────────────── #

def not_connected_view() -> ui.UINode:
    return ui.Stack([
        ui.Empty(
            message="No Meta Ads account connected.",
            icon="Target",
            action=ui.Send("Connect Meta Ads"),
        ),
    ])


def needs_setup_view() -> ui.UINode:
    return ui.Stack([
        ui.Alert(type="warn",
                 message="Ad accounts discovered. Select one to continue."),
        ui.Button(label="Setup account", variant="primary", full_width=True,
                  on_click=ui.Send("Setup my Meta Ads account")),
    ])


def error_view(msg: str) -> ui.UINode:
    return ui.Stack([
        ui.Alert(type="error", message=msg[:200]),
        ui.Button(label="Reconnect", variant="ghost",
                  on_click=ui.Send("Reconnect Meta Ads")),
    ])
