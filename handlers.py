"""Meta Ads · Account management handlers.

Functions: connect, status, setup_account, switch_account, disconnect.

Phase 1: The server uses a shared META_ACCESS_TOKEN. Users "connect" by
selecting an ad account from those accessible via the server token.
Phase 2: Per-user OAuth via Auth Gateway (redirect URI already configured).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app import chat, ActionResult, _no_account_error
from meta_providers.helpers import (
    _all_accounts,
    _active_account,
    COLLECTION,
)
from meta_providers.meta_client import list_ad_accounts, get_account


# ─── Models ───────────────────────────────────────────────────────────────── #

class SetupAccountParams(BaseModel):
    """Select a Meta Ads account after discovery."""
    ad_account_id: str = Field(
        default="",
        description=(
            "Ad account ID to activate (e.g. act_1132513062349595). "
            "Omit to list all available accounts."
        ),
    )


class AccountParams(BaseModel):
    """Target a specific account by ID or name."""
    account: str = Field(description="Ad account ID or account name")


# ─── connect ──────────────────────────────────────────────────────────────── #

@chat.function(
    "connect",
    action_type="write",
    description=(
        "Connect a Meta (Facebook/Instagram) Ads account. "
        "Discovers all accessible ad accounts and guides through selection. "
        "Call this first to get started."
    ),
)
async def fn_connect(ctx) -> ActionResult:
    accounts = await _all_accounts(ctx)

    # Already fully connected
    ready = [a for a in accounts if a.get("ad_account_id") and not a.get("_needs_setup")]
    if ready:
        active = next((a for a in ready if a.get("is_active")), ready[0])
        return ActionResult.success(
            data={
                "already_connected": True,
                "account_name":   active.get("account_name", ""),
                "ad_account_id":  active.get("ad_account_id", ""),
                "total_accounts": len(ready),
            },
            summary=f"Already connected: {active.get('account_name', active.get('ad_account_id'))}",
        )

    # Discover ad accounts from microservice
    discovered = await list_ad_accounts(ctx)
    if not discovered:
        return ActionResult.error(
            "No Meta ad accounts found. "
            "Ensure the Meta App has access to at least one Business ad account.",
            retryable=True,
        )

    # Auto-activate if only one account
    if len(discovered) == 1:
        acc = discovered[0]
        await ctx.store.create(COLLECTION, {
            "ad_account_id": acc["id"],
            "account_name":  acc.get("name", acc["id"]),
            "currency":      acc.get("currency", "USD"),
            "is_active":     True,
            "_needs_setup":  False,
        })
        return ActionResult.success(
            data={
                "connected":     True,
                "ad_account_id": acc["id"],
                "account_name":  acc.get("name", acc["id"]),
                "currency":      acc.get("currency", "USD"),
            },
            summary=f"Meta Ads connected: {acc.get('name', acc['id'])}",
        )

    # Multiple accounts — store them as pending, ask user to select
    for acc in discovered:
        await ctx.store.create(COLLECTION, {
            "ad_account_id": acc["id"],
            "account_name":  acc.get("name", acc["id"]),
            "currency":      acc.get("currency", "USD"),
            "is_active":     False,
            "_needs_setup":  True,
        })

    return ActionResult.success(
        data={
            "needs_setup":        True,
            "available_accounts": [
                {"id": a["id"], "name": a.get("name", a["id"]), "currency": a.get("currency")}
                for a in discovered
            ],
        },
        summary=f"Found {len(discovered)} ad accounts. Say 'setup Meta Ads account' to select one.",
    )


# ─── status ───────────────────────────────────────────────────────────────── #

@chat.function(
    "status",
    action_type="read",
    description="Show all connected Meta Ads accounts and today's summary stats.",
)
async def fn_status(ctx) -> ActionResult:
    accounts = await _all_accounts(ctx)
    if not accounts:
        return ActionResult.success(
            data={"connected": False, "accounts": [], "total": 0},
            summary="No Meta Ads account connected.",
        )

    skeleton_data = await ctx.skeleton.get("meta_ads_account") or {}
    today = skeleton_data.get("today", {})

    result = [
        {
            "ad_account_id": a.get("ad_account_id", ""),
            "account_name":  a.get("account_name", ""),
            "currency":      a.get("currency", ""),
            "is_active":     a.get("is_active", False),
            "_needs_setup":  a.get("_needs_setup", False),
        }
        for a in accounts
    ]
    return ActionResult.success(
        data={"connected": True, "accounts": result, "total": len(result), "today": today},
        summary=f"{len(result)} Meta Ads account(s) connected.",
    )


# ─── setup_account ────────────────────────────────────────────────────────── #

@chat.function(
    "setup_account",
    action_type="write",
    event="account_connected",
    description=(
        "Select and activate a Meta Ads account from the discovered list. "
        "Call after 'connect' when multiple accounts are available. "
        "Omit ad_account_id to list all available options."
    ),
)
async def fn_setup_account(ctx, params: SetupAccountParams) -> ActionResult:
    accounts = await _all_accounts(ctx)
    if not accounts:
        return ActionResult.error(
            "No accounts found. Say 'connect Meta Ads' first.", retryable=False
        )

    if not params.ad_account_id:
        return ActionResult.success(
            data={"available_accounts": [
                {"ad_account_id": a["ad_account_id"], "account_name": a.get("account_name", "")}
                for a in accounts
            ], "needs_selection": True},
            summary=f"Found {len(accounts)} account(s). Specify ad_account_id to activate.",
        )

    target = next(
        (a for a in accounts
         if a.get("ad_account_id") == params.ad_account_id
         or a.get("account_name") == params.ad_account_id),
        None,
    )
    if not target:
        available = [a.get("account_name", a.get("ad_account_id")) for a in accounts]
        return ActionResult.error(
            f"Account {params.ad_account_id!r} not found. Available: {available}",
            retryable=False,
        )

    # Deactivate all others, activate target
    for a in accounts:
        is_target = a.get("ad_account_id") == target["ad_account_id"]
        await ctx.store.update(COLLECTION, a["doc_id"], {
            **{k: v for k, v in a.items() if k != "doc_id"},
            "is_active":    is_target,
            "_needs_setup": False,
        })

    return ActionResult.success(
        data={
            "ad_account_id": target["ad_account_id"],
            "account_name":  target.get("account_name", ""),
            "currency":      target.get("currency", "USD"),
        },
        summary=f"Meta Ads account '{target.get('account_name', target['ad_account_id'])}' activated.",
    )


# ─── switch_account ───────────────────────────────────────────────────────── #

@chat.function(
    "switch_account",
    action_type="write",
    event="account_switched",
    description="Switch the active Meta Ads account.",
)
async def fn_switch_account(ctx, params: AccountParams) -> ActionResult:
    accounts = await _all_accounts(ctx)
    if not accounts:
        return _no_account_error()

    target = next(
        (a for a in accounts
         if a.get("ad_account_id") == params.account
         or a.get("account_name")  == params.account),
        None,
    )
    if not target:
        available = [a.get("account_name", a.get("ad_account_id")) for a in accounts]
        return ActionResult.error(f"Account not found. Available: {available}", retryable=False)

    for a in accounts:
        is_target = a.get("ad_account_id") == target["ad_account_id"]
        if a.get("is_active") != is_target:
            await ctx.store.update(COLLECTION, a["doc_id"], {
                **{k: v for k, v in a.items() if k != "doc_id"},
                "is_active": is_target,
            })

    return ActionResult.success(
        data={"switched": True, "ad_account_id": target.get("ad_account_id"),
              "account_name": target.get("account_name")},
        summary=f"Switched to {target.get('account_name', target.get('ad_account_id'))}.",
    )


# ─── disconnect ───────────────────────────────────────────────────────────── #

@chat.function(
    "disconnect",
    action_type="destructive",
    event="account_disconnected",
    description="Remove a connected Meta Ads account.",
)
async def fn_disconnect(ctx, params: AccountParams) -> ActionResult:
    accounts = await _all_accounts(ctx)
    target = next(
        (a for a in accounts
         if a.get("ad_account_id") == params.account
         or a.get("account_name")  == params.account),
        None,
    )
    if not target:
        return ActionResult.error("Account not found.", retryable=False)

    await ctx.store.delete(COLLECTION, target["doc_id"])
    return ActionResult.success(
        data={
            "disconnected":  True,
            "ad_account_id": target.get("ad_account_id", ""),
            "account_name":  target.get("account_name", ""),
            "remaining":     len(accounts) - 1,
        },
        summary=f"Disconnected {target.get('account_name', target.get('ad_account_id'))}.",
    )
