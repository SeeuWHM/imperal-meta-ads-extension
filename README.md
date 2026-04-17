# imperal-meta-ads-extension

[![Imperal SDK](https://img.shields.io/badge/imperal--sdk-1.5.7-blue)](https://pypi.org/project/imperal-sdk/)
[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://github.com/SeeuWHM/imperal-meta-ads-extension/releases)
[![License](https://img.shields.io/badge/license-LGPL--2.1-orange)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Imperal%20Cloud-purple)](https://panel.imperal.io)

**Meta (Facebook & Instagram) Ads AI manager extension for [Imperal Cloud](https://panel.imperal.io).**

Connect your Meta Ads account and manage campaigns, ad sets, ads, creatives, and custom audiences through natural language.

---

## What It Does

Talk to it naturally:

```
"connect my Meta Ads account"
"show me all active campaigns"
"pause the Summer Sale campaign"
"create a Traffic campaign with $50 daily budget"
"create an ad set targeting US users aged 25-45"
"show performance for the last 7 days"
"what's my ROAS this month?"
"create a custom audience from my email list"
"analyse my Meta Ads performance"
"check my budget status"
```

Or manage everything from the panel — left sidebar shows account KPIs and campaign list, right panel shows campaign detail, ad sets, and performance chart.

---

## Capabilities

### Account Management
| Action | Description |
|--------|-------------|
| **connect** | Discover ad accounts via server-side Meta API token |
| **status** | Current account, today's KPIs, budget alerts |
| **setup_account** | Select and activate an ad account from the discovered list |
| **switch_account** | Switch between multiple connected ad accounts |
| **disconnect** | Remove account from Imperal |

### Campaigns
| Action | Description |
|--------|-------------|
| **list_campaigns** | All campaigns with status, objective, and today's spend |
| **get_campaign** | Campaign detail + ad sets |
| **create_campaign** | Traffic / Leads / Sales / Awareness / Engagement / App Promotion |
| **update_campaign** | Name, status, budget (CBO), bid strategy |
| **pause_campaign** | One-click pause — stops all ad delivery |
| **resume_campaign** | One-click activate |

### Ad Sets
| Action | Description |
|--------|-------------|
| **list_ad_sets** | Ad sets by campaign with budget and status |
| **get_ad_set** | Ad set detail including full targeting spec |
| **create_ad_set** | Daily budget (USD), geo/age/gender targeting, optimization goal |
| **update_ad_set** | Name, status, daily budget |
| **pause_ad_set** | Pause ad set |
| **resume_ad_set** | Resume ad set |

### Ads
| Action | Description |
|--------|-------------|
| **list_ads** | Ads by ad set |
| **get_ad** | Ad detail with attached creative |
| **create_ad** | Link ad set to creative (creative_id required) |
| **update_ad** | Name, status, or swap creative |

### Creatives
| Action | Description |
|--------|-------------|
| **list_creatives** | Creative library with name and destination URL |
| **get_creative** | Creative detail |
| **create_creative** | Link ad with page_id, destination URL, ad copy, CTA, optional image_hash |

### Audiences
| Action | Description |
|--------|-------------|
| **list_audiences** | Custom audiences with size and type |
| **get_audience** | Audience detail with approximate count |
| **create_audience** | CUSTOM / WEBSITE / APP / LOOKALIKE / ENGAGEMENT |
| **add_audience_users** | Upload hashed user data (EMAIL / PHONE / EXTERN_ID, max 10K/call) |

### Reports & AI Analysis
| Action | Description |
|--------|-------------|
| **get_performance** | Account / campaign / ad_set / ad level insights |
| **get_budget_status** | Today: spend vs budget with utilisation % and alerts |
| **analyze_performance** | AI insights via `ctx.ai` — trends, ROAS assessment, 3 recommendations |

---

## Panel UI

Built on [Imperal Declarative UI](https://github.com/imperalcloud/imperal-sdk) — zero custom React.

```
┌──── Left Panel (account_dashboard) ────────┐  ┌──── Right Panel (campaign_detail) ─────────────┐
│  Meta Ads                                  │  │  Summer Sale                      ACTIVE        │
│  ID: act_1132513062349595                  │  │  ID: 120201234567890   Objective: Sales         │
│  ──────────────────────────────────────    │  │  Budget: $50.00/day   Bid: Lowest Cost          │
│  $18.40 spend / $250 budget · 7%           │  │  ─────────────────────────────────────────────  │
│  ──────────────────────────────────────    │  │  [Today] [Ad Sets (3)]                          │
│  Spend Today  Clicks  Impressions  CTR     │  │                                                  │
│  $18.40       142     4,230        3.36%   │  │  ▰▰▰░░░░░░░░  7% of budget                     │
│  ──────────────────────────────────────    │  │  Spend Today   Clicks   CTR   Conversions        │
│  CAMPAIGNS · 2 active  1 paused            │  │  $18.40        142      3%    4                  │
│    Summer Sale  ACTIVE  $18.40  ▮Pause     │  │  ─────────────────────────────────────────────  │
│    Brand        ACTIVE  $2.10   ▮Pause     │  │  Ad Sets (3)                                    │
│    Retargeting  PAUSED  —       ▮Resume    │  │    US Lookalike   ACTIVE  $20/day               │
│                                            │  │    EU Targeting   ACTIVE  $20/day               │
│  [+ Campaign]  [↺]                         │  │    Retargeting    PAUSED  $10/day               │
└────────────────────────────────────────────┘  │  [+ Ad Set]                                     │
                                                │  [Pause] [7-day report] [AI Analyse]            │
                                                └─────────────────────────────────────────────────┘
```

---

## File Structure

```
imperal-meta-ads-extension/
├── main.py                  # Entry point — sys.modules cleanup + imports
├── app.py                   # Extension setup, ChatExtension, helpers, health check
├── handlers.py              # connect, status, setup_account, switch_account, disconnect
├── handlers_campaigns.py    # list/get/create/update/pause/resume campaigns
├── handlers_ad_sets.py      # list/get/create/update/pause/resume ad sets
├── handlers_ads.py          # list/get/create/update ads
├── handlers_creatives.py    # list/get/create creatives
├── handlers_insights.py     # get_performance, get_budget_status, analyze_performance (AI)
├── handlers_audiences.py    # list/get/create audiences + add_audience_users
├── skeleton.py              # skeleton_refresh_meta_ads + skeleton_alert_meta_ads
├── panels.py                # Left panel: account dashboard + campaign list
├── panels_campaign.py       # Right panel: campaign detail (today perf + ad sets)
├── panels_ui.py             # Shared formatters, badge helpers, state views
├── system_prompt.txt        # LLM system prompt
├── imperal.json             # Extension manifest
└── meta_providers/          # Internal package — helpers, HTTP client
    ├── __init__.py
    ├── helpers.py           # Constants, COLLECTION, account helpers, budget converters
    └── meta_client.py       # HTTP client → whm-meta-ads-control microservice (:8091)
```

---

## Architecture

```
User (chat)
    ↓
Extension → HTTP → whm-meta-ads-control (:8091 on api-server)
    Authorization: Bearer META_JWT
    ?ad_account_id=act_XXXXX  (per-request query param)
    ↓ microservice (facebook-business SDK) → Meta Marketing API v21+ (Graph API)
```

**Phase 1 (current):** Server-side `META_ACCESS_TOKEN` shared for all users. Users connect by selecting from ad accounts accessible via the server token.

**Phase 2 (planned):** Per-user OAuth via Auth Gateway. Redirect URI already configured: `https://auth.imperal.io/v1/oauth/meta-ads/callback`. Facebook App: `imperal-extension` (App ID: `1662599881607889`).

**Budget units:** Meta API stores budgets in **cents**. The extension accepts USD input from users and converts automatically (`$50.00 → 5000 cents`).

---

## Skeleton

| Tool | Description |
|------|-------------|
| `skeleton_refresh_meta_ads` | Today's KPIs (spend/clicks/impressions/CTR/conversions), campaign list with budget %, alerts |
| `skeleton_alert_meta_ads` | `notify()` when any campaign reaches ≥90% of daily budget |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `META_JWT` | — | Service JWT for microservice auth |
| `META_API_URL` | `https://api.webhostmost.com/meta-ads` | Microservice URL |
| `META_APP_ID` | `1662599881607889` | Meta App ID (for Phase 2 OAuth) |
| `META_APP_SECRET` | — | Meta App Secret (for Phase 2 OAuth) |
| `META_REDIRECT_URI` | `https://auth.imperal.io/v1/oauth/meta-ads/callback` | OAuth callback URI |

---

## Built with

- [imperal-sdk](https://github.com/imperalcloud/imperal-sdk) 1.5.7
- [Imperal Cloud](https://panel.imperal.io)
- Meta Marketing API v21+ via [facebook-business](https://github.com/facebook/facebook-python-business-sdk) (microservice layer)
