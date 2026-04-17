"""Meta Ads Extension v1.0.0 · Meta (Facebook / Instagram) Ads AI management."""
from __future__ import annotations

import sys
import os

# ─── Module isolation (mandatory — prevents cross-extension import cache) ──── #
_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)
for _m in [k for k in sys.modules if k in (
    "app", "handlers", "handlers_campaigns", "handlers_ad_sets",
    "handlers_ads", "handlers_creatives", "handlers_insights",
    "handlers_audiences", "skeleton",
    "panels", "panels_campaign", "panels_ui",
    "meta_providers", "meta_providers.helpers", "meta_providers.meta_client",
)]:
    del sys.modules[_m]

# ─── Extension entry points ────────────────────────────────────────────────── #

from app import ext, chat          # noqa: F401 — registers Extension + ChatExtension
import handlers                    # noqa: F401 — account management
import handlers_campaigns          # noqa: F401 — campaign CRUD
import handlers_ad_sets            # noqa: F401 — ad set CRUD
import handlers_ads                # noqa: F401 — ad CRUD
import handlers_creatives          # noqa: F401 — creative management
import handlers_insights           # noqa: F401 — performance reports + AI analysis
import handlers_audiences          # noqa: F401 — custom audiences
import skeleton                    # noqa: F401 — background refresh + alerts
import panels                      # noqa: F401 — left panel: account dashboard
import panels_campaign             # noqa: F401 — right panel: campaign detail
