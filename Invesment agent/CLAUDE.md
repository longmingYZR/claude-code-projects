# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

```bash
python agent.py                          # Process all articles in config (auto-discovers new ones from column)
python agent.py <url>                    # Process a single article
python agent.py --force                  # Re-process already-handled articles
python agent.py <url> --force            # Re-process a single article
python agent.py --scheduler              # Start daily timer (08:30 Asia/Shanghai)
```

Dependencies are in `requirements.txt`, but **two extra packages are required** beyond what the file lists:
```bash
pip install -r requirements.txt
pip install playwright akshare
```

The project runs on **Windows**, using Edge as the Playwright browser channel (Chrome is not installed on this machine).

## Architecture

The pipeline is `agent.py → fetcher.py → analyzer.py → database.py → notifier.py`, with `market_data.py` providing live market context.

### Fetcher (`fetcher.py`) — zhihu paid column scraping

Uses **Playwright + Edge browser** (not plain requests) because Zhihu serves a `zse_ck` JavaScript challenge that requires a real browser.

- `_browser_page()` is a shared context manager that launches Edge headless, loads cookies from config, visits zhihu.com to establish session, then yields a page object.
- `_parse_cookies()` converts the raw cookie string from `config.py` into Playwright's cookie dict format.
- `fetch_article(url)` navigates to a single article, extracts title/content/publish_date via BeautifulSoup. Content is trimmed to 8000 chars before being sent to the AI.
- `discover_new_articles(known_urls)` scrapes the column page for `/p/` links and returns URLs not already in the database.

Known anti-bot signals: if `<meta id="zh-zse-ck">` appears or HTML < 2000 bytes, the page was blocked.

### Analyzer (`analyzer.py`) — two-step DeepSeek AI pipeline

Step 1 — `extract_signals(article)`: Sends article content to DeepSeek with a strict JSON schema prompt. Returns structured `{summary, is_actionable, directional_views[], key_price_levels[]}`. JSON is cleaned of markdown code fences before parsing.

Step 2 — `generate_investment_advice(...)`: Takes the extracted signals PLUS historical views from DB, active key price levels, and live market snapshot. This composite prompt produces a Feishu-formatted advice message with emoji sections.

### Database (`database.py`) — SQLite with three tables

- **articles**: URL is UNIQUE. Re-processing updates the row via `ON CONFLICT DO UPDATE`.
- **directional_views**: `is_latest=1` marks the current view. When a new view comes in for the same `asset_class`, the old one gets `is_latest=0` and `valid_until` set. This implements automatic view lifecycle tracking.
- **key_price_levels**: Deduplication uses 0.5% price tolerance — if a new level is within 0.5% of an existing one with the same `asset_code` and `level_type`, `mention_count` is incremented instead of creating a duplicate row.

### Market data (`market_data.py`) — AKShare live quotes

Fetches A-share indices via `stock_zh_index_spot_sina()` (Sina API) and SHFE silver futures via `futures_zh_daily_sina(symbol="AG0")`.

Silver price is displayed in both CNY/kg and USD/oz using the conversion: `price_usd_oz = price_cny_kg / 32.1507 / usdcny_rate`. The exchange rate is hardcoded at 7.25 because AKShare's FX APIs return stale data (~6.80 from 2022). The resulting USD/oz price reflects the **Shanghai domestic price**, which carries a $5–15 premium above COMEX due to import duties, VAT, and local supply/demand.

### Agent (`agent.py`) — orchestrator

`process_article()` runs the full pipeline. Key behaviors:
- Articles with `is_actionable=false` are saved to DB but NOT pushed to Feishu.
- Before generating advice, it queries `get_latest_views()` and `get_active_price_levels()` to provide historical context.
- `run_all()` merges manually configured URLs with auto-discovered ones, then processes each.

On Windows, stdout/stderr are wrapped with `utf-8` encoding to handle emoji output in CMD.

### Notifier (`notifier.py`) — Feishu webhook

Sends Feishu interactive card messages (blue header for actionable articles, grey for non-actionable). Falls back to plain text if the card API fails. `send_error_alert()` sends a separate text message for pipeline errors.

## Key design decisions

- **Cookie format**: Must be the full cookie string from browser DevTools (14+ fields), not just `z_c0`. Stored as a Python string in `config.py`, parsed by `_parse_cookies()` for Playwright.
- **View replacement**: Only one active view per `asset_class` at a time — inserting a new one auto-invalidates the old. This matches the blogger's behavior of updating views rather than adding conflicting ones.
- **Price level dedup**: Uses 0.5% tolerance rather than exact match, so "3000点" and "3010点" across different articles are treated as the same level.
- **Silver pricing**: The system CANNOT get COMEX prices directly (yfinance is rate-limited, AKShare `futures_foreign_hist` doesn't support COMEX). The SHFE-to-USD conversion with Shanghai premium explanation is the current workaround.
- **Network restriction**: The project runs behind a proxy (127.0.0.1:7890) that may or may not be active. If pip/API calls fail with connection errors, check proxy status.
