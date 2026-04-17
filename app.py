"""Meta Ads · Extension setup, shared helpers, health check."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from imperal_sdk import Extension, Context
from imperal_sdk.chat import ChatExtension, ActionResult

from meta_providers.helpers import (
    _all_accounts,
    _active_account,
    COLLECTION,
    META_API_URL,
    META_JWT,
)

log = logging.getLogger("meta-ads")

# ─── System Prompt ────────────────────────────────────────────────────────── #

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text()

# ─── Extension ────────────────────────────────────────────────────────────── #

ext = Extension("meta-ads", version="1.0.0")

chat = ChatExtension(
    ext=ext,
    tool_name="tool_meta_ads_chat",
    description=(
        "Meta Ads — connect Facebook/Instagram ad account, manage campaigns "
        "(Traffic/Leads/Sales/Awareness/Engagement/App Promotion), ad sets with targeting, "
        "ads, creatives, custom audiences, performance insights (impressions/clicks/spend/ROAS), "
        "budget monitoring, AI performance analysis."
    ),
    system_prompt=SYSTEM_PROMPT,
    model="claude-haiku-4-5-20251001",
)


# ─── Shared error helpers ─────────────────────────────────────────────────── #

def _no_account_error() -> ActionResult:
    return ActionResult.error(
        "No Meta Ads account connected. Say 'connect Meta Ads' to get started.",
        retryable=False,
    )


def _needs_setup_error() -> ActionResult:
    return ActionResult.error(
        "Meta Ads account found but not selected yet. "
        "Say 'setup Meta Ads account' to choose your ad account.",
        retryable=False,
    )


async def _get_ready_account(
    ctx: Context, account: str = ""
) -> tuple[Optional[dict], Optional[ActionResult]]:
    """Resolve the active account, returning (acc, None) on success
    or (None, ActionResult.error(...)) when not usable.
    """
    acc = await _active_account(ctx, account)
    if not acc:
        return None, _no_account_error()
    if acc.get("_needs_setup"):
        return None, _needs_setup_error()
    return acc, None


# ─── Health Check ─────────────────────────────────────────────────────────── #

@ext.health_check
async def health(ctx) -> dict:
    """Verify microservice connectivity and report connected accounts."""
    accounts = await _all_accounts(ctx)
    try:
        r = await ctx.http.get(
            f"{META_API_URL}/health",
            headers={"Authorization": f"Bearer {META_JWT}"},
        )
        svc_status = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        svc_status = "unreachable"

    return {
        "status":             "ok" if svc_status == "ok" else "degraded",
        "version":            ext.version,
        "accounts_connected": len([a for a in accounts if not a.get("_needs_setup")]),
        "microservice":       svc_status,
    }
