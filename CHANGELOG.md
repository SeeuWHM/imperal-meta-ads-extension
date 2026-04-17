# Changelog

## [1.0.0] — 2026-04-18

### Added
- Phase 1 account connection: discover ad accounts via server-side META_ACCESS_TOKEN, no per-user OAuth required
- 28 chat functions across 8 domains:
  - Account management (5): connect, status, setup_account, switch_account, disconnect
  - Campaigns (6): list_campaigns, get_campaign, create_campaign, update_campaign, pause_campaign, resume_campaign
  - Ad Sets (6): list_ad_sets, get_ad_set, create_ad_set, update_ad_set, pause_ad_set, resume_ad_set
  - Ads (4): list_ads, get_ad, create_ad, update_ad
  - Creatives (3): list_creatives, get_creative, create_creative
  - Insights (3): get_performance, get_budget_status, analyze_performance
  - Audiences (4): list_audiences, get_audience, create_audience, add_audience_users
- Campaign objectives: OUTCOME_TRAFFIC, OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_AWARENESS, OUTCOME_ENGAGEMENT, OUTCOME_APP_PROMOTION
- Bid strategies: LOWEST_COST_WITHOUT_CAP, LOWEST_COST_WITH_BID_CAP, COST_CAP, LOWEST_COST_WITH_MIN_ROAS
- Ad set targeting: geo (countries), age range, gender, optimization goal, destination type
- Creative creation: page_id, destination URL, ad copy, CTA, optional image_hash
- Custom audience upload: SHA256-hashed EMAIL / PHONE / EXTERN_ID, max 10K users/request
- Budget conversion: user USD input → Meta cents internally (transparent to user)
- Performance insights at account / campaign / ad_set / ad levels with Meta date presets
- AI performance analysis via `ctx.ai` (Claude Sonnet) — trends, ROAS assessment, 3 recommendations
- Budget monitoring: today's spend vs daily budget with utilisation % and over-90% alerts
- Skeleton tools: `skeleton_refresh_meta_ads` (today's KPIs + campaign list) + `skeleton_alert_meta_ads` (budget alerts via notify)
- 2 panels: account dashboard with KPI stats and campaign list (left), campaign detail with today's performance chart and ad sets (right)
- Health check endpoint: verifies microservice connectivity
- `meta_providers/` package: constants, account helpers, budget converters, HTTP client for all 42 microservice endpoints
