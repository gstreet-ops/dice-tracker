"""
generate.py — Generates the GitHub Pages dashboard HTML.
Reads from Supabase and writes dashboard/index.html.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import get_supabase
from datetime import datetime
import logging

logger = logging.getLogger("dashboard")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "index.html")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
GITHUB_REPO = "gstreet-ops/dice-tracker"
GITHUB_WORKFLOW = "scrape.yml"


def generate_dashboard():
    sb = get_supabase()
    products = _fetch_products(sb)
    run_stats = _fetch_run_stats(sb)
    watchlist = _fetch_watchlist(sb)
    html = _render(products, run_stats, watchlist)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Dashboard written ({len(products)} products)")


def _fetch_products(sb):
    result = (
        sb.table("products")
        .select("id, title, url, source, score, size_mm, finish, material, pip_style, last_seen, is_excluded, watchlist_category")
        .eq("is_excluded", False)
        .order("score", desc=True)
        .limit(100)
        .execute()
    )
    products = result.data or []
    for p in products:
        ph = (
            sb.table("price_history")
            .select("price_usd, in_stock, scraped_at")
            .eq("product_id", p["id"])
            .order("scraped_at", desc=True)
            .limit(1)
            .execute()
        )
        if ph.data:
            p["price_usd"] = ph.data[0]["price_usd"]
            p["in_stock"] = ph.data[0]["in_stock"]
        else:
            p["price_usd"] = None
            p["in_stock"] = None
    return products


def _fetch_run_stats(sb):
    try:
        result = (
            sb.table("run_log")
            .select("ran_at, results_found, new_products, price_drops")
            .order("ran_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else {}
    except Exception:
        return {}


def _fetch_watchlist(sb):
    try:
        result = (
            sb.table("watchlist")
            .select("id, name, keywords, max_price, is_active, created_at")
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def _relative_time(iso_str: str) -> str:
    """Convert ISO timestamp to human-readable relative time."""
    if not iso_str:
        return "\u2014"
    try:
        from datetime import timezone
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        mins = int(diff.total_seconds() / 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days == 1:
            return "yesterday"
        return f"{days}d ago"
    except Exception:
        return "\u2014"


def _render(products, stats, watchlist):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    last_run = stats.get("ran_at", "unknown")[:16].replace("T", " ") if stats.get("ran_at") else "unknown"
    total = len(products)
    in_stock = sum(1 for p in products if p.get("in_stock"))

    rows = ""
    for p in products:
        score = p.get("score", 0)
        score_color = "#27ae60" if score >= 70 else "#f39c12" if score >= 40 else "#e74c3c"
        price = f"${p['price_usd']:.2f}" if p.get("price_usd") else "\u2014"
        stock_badge = (
            '<span style="color:#27ae60;font-weight:500">In stock</span>'
            if p.get("in_stock")
            else '<span style="color:#e74c3c">Out of stock</span>'
        )
        size = f"{p['size_mm']}mm" if p.get("size_mm") else "\u2014"
        category = p.get("watchlist_category") or "Dice"
        last_seen_raw = p.get("last_seen") or ""
        found_label = _relative_time(last_seen_raw)
        rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee">
            <a href="{p['url']}" target="_blank" style="color:#0066cc;font-weight:500;text-decoration:none">
              {p['title'][:65]}
            </a><br>
            <span style="font-size:12px;color:#888">{p['source']}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center">
            <span style="background:#f0f0f0;padding:2px 8px;border-radius:4px;font-size:12px">{category}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center">{size}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:500">{price}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center">{stock_badge}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center">
            <span style="color:{score_color};font-weight:600">{score}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center;font-size:12px;color:#aaa">{found_label}</td>
        </tr>"""

    # Pre-render watchlist items for the static HTML
    watchlist_json = "[]"
    if watchlist:
        import json
        watchlist_json = json.dumps(watchlist)

    return _html_template(now, last_run, total, in_stock,
                          stats.get('new_products', 0), rows,
                          SUPABASE_URL, SUPABASE_ANON_KEY,
                          GITHUB_REPO, GITHUB_WORKFLOW, watchlist_json)


def _html_template(now, last_run, total, in_stock, new_count, rows,
                   supabase_url, supabase_key, github_repo, github_workflow,
                   watchlist_json):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Product Tracker</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f7f7f7;color:#1a1a1a}}
    .header{{background:#fff;border-bottom:1px solid #e5e5e5;padding:0 24px;display:flex;align-items:center;gap:24px}}
    .header h1{{font-size:18px;font-weight:600;padding:16px 0}}
    .nav{{display:flex;gap:0}}
    .nav a{{padding:18px 16px;font-size:14px;color:#555;text-decoration:none;border-bottom:2px solid transparent;cursor:pointer}}
    .nav a.active{{color:#1a1a1a;border-bottom:2px solid #1a1a1a;font-weight:500}}
    .nav a:hover{{color:#1a1a1a}}
    .page{{display:none;max-width:960px;margin:0 auto;padding:28px 24px}}
    .page.active{{display:block}}
    .stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}}
    .stat{{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:16px 20px}}
    .stat-val{{font-size:28px;font-weight:600}}
    .stat-lbl{{font-size:12px;color:#888;margin-top:4px}}
    .card{{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:20px 24px;margin-bottom:16px}}
    table{{width:100%;border-collapse:collapse;font-size:14px}}
    th{{background:#fafafa;padding:10px 8px;text-align:left;font-weight:500;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #eee}}
    tr:hover td{{background:#fafafa}}
    .meta{{color:#999;font-size:13px;margin-bottom:20px}}
    .setting-row{{padding:18px 0;border-bottom:1px solid #f0f0f0}}
    .setting-row:last-child{{border-bottom:none}}
    .setting-label{{font-weight:500;font-size:14px;margin-bottom:3px}}
    .setting-desc{{font-size:12px;color:#888;margin-bottom:10px}}
    input[type=text],input[type=number],input[type=password],select,textarea{{width:100%;padding:9px 12px;border:1px solid #ddd;border-radius:7px;font-size:14px;font-family:inherit;background:#fafafa}}
    input:focus,select:focus,textarea:focus{{outline:none;border-color:#666;background:#fff}}
    .btn{{padding:9px 20px;border-radius:7px;font-size:14px;cursor:pointer;font-family:inherit;border:none;font-weight:500;display:inline-flex;align-items:center;gap:6px}}
    .btn-primary{{background:#1a1a1a;color:#fff}}
    .btn-primary:hover{{background:#333}}
    .btn-primary:disabled{{background:#999;cursor:not-allowed}}
    .btn-green{{background:#27ae60;color:#fff}}
    .btn-green:hover{{background:#219a52}}
    .btn-green:disabled{{background:#aaa;cursor:not-allowed}}
    .btn-secondary{{background:#f0f0f0;color:#333;border:1px solid #ddd}}
    .btn-danger{{background:#fff;color:#e74c3c;border:1px solid #e74c3c}}
    .btn-danger:hover{{background:#fef5f5}}
    .toast{{position:fixed;bottom:24px;right:24px;background:#1a1a1a;color:#fff;padding:12px 20px;border-radius:8px;font-size:14px;opacity:0;transition:opacity .3s;pointer-events:none;z-index:999}}
    .toast.show{{opacity:1}}
    .watchlist-item{{display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid #f0f0f0}}
    .watchlist-item:last-child{{border-bottom:none}}
    .watchlist-name{{font-weight:500;font-size:14px;flex:1}}
    .watchlist-keywords{{font-size:12px;color:#888;flex:2}}
    .watchlist-price{{font-size:13px;color:#555;width:80px;text-align:right}}
    .run-status{{display:inline-block;font-size:12px;padding:3px 10px;border-radius:999px;background:#e8f5e9;color:#27ae60;font-weight:500}}
    .run-status.running{{background:#fff8e1;color:#f39c12}}
    .header-right{{display:flex;align-items:center;gap:14px;margin-left:auto}}
    .pulse-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;background:#f39c12;margin-right:6px;animation:pulse 1.2s ease-in-out infinite}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
    a{{color:#0066cc}}
    .divider{{border:none;border-top:1px solid #f0f0f0;margin:20px 0}}
  </style>
</head>
<body>
<div class="header">
  <h1>Product Tracker</h1>
  <nav class="nav">
    <a class="active" id="nav-results" data-page="results">Results</a>
    <a href="analytics.html" style="color:#555">Analytics</a>
    <a id="nav-watchlist" data-page="watchlist">Watchlist</a>
    <a id="nav-sources" data-page="sources">Sources</a>
    <a id="nav-settings" data-page="settings">Settings</a>
    <a href="roadmap.html" style="color:#888">Roadmap &#8599;</a>
  </nav>
  <div class="header-right">
    <span id="run-status-indicator" style="font-size:12px;color:#888"></span>
    <button class="btn btn-green" id="header-run-btn">
      <span>&#9654;</span> Run search now
    </button>
  </div>
</div>

<!-- RESULTS -->
<div id="page-results" class="page active">
  <div style="margin-bottom:20px">
    <p class="meta" style="margin:0">Last updated: {now} &nbsp;&middot;&nbsp; Last search: {last_run}</p>
  </div>
  <div class="stats">
    <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Products found</div></div>
    <div class="stat"><div class="stat-val">{in_stock}</div><div class="stat-lbl">In stock now</div></div>
    <div class="stat"><div class="stat-val">{new_count}</div><div class="stat-lbl">New this run</div></div>
  </div>
  <div class="card">
    <table>
      <thead><tr>
        <th>Product</th>
        <th style="text-align:center">Category</th>
        <th style="text-align:center">Size</th>
        <th style="text-align:right">Price</th>
        <th style="text-align:center">Stock</th>
        <th style="text-align:center">Score</th>
        <th style="text-align:center">Found</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:20px;font-size:12px;color:#bbb">Score: 70+ = strong &nbsp;&middot;&nbsp; 40&ndash;69 = partial &nbsp;&middot;&nbsp; below 40 = weak</p>
  </div>
</div>

<!-- WATCHLIST -->
<div id="page-watchlist" class="page">
  <div style="margin-bottom:20px">
    <h2 style="font-size:18px;font-weight:600;margin-bottom:4px">Watchlist</h2>
    <p class="meta" style="margin:0">Add product categories to search for. Each item runs as a separate search.</p>
  </div>

  <!-- Add new item form -->
  <div class="card" id="watchlist-form-card">
    <h3 style="font-size:14px;font-weight:600;margin-bottom:14px">Add watchlist item</h3>
    <div style="display:grid;grid-template-columns:1fr 2fr auto;gap:12px;align-items:end">
      <div>
        <div class="setting-label">Name</div>
        <input type="text" id="wl-name" placeholder="e.g. Brass Bookends">
      </div>
      <div>
        <div class="setting-label">Keywords <span style="font-weight:400;color:#888">(one per line)</span></div>
        <textarea id="wl-keywords" rows="2" placeholder="brass bookends vintage&#10;heavy brass bookend set"></textarea>
      </div>
      <div>
        <div class="setting-label">Max price (USD)</div>
        <div style="display:flex;gap:8px;align-items:end">
          <input type="number" id="wl-maxprice" placeholder="optional" style="width:100px">
          <button class="btn btn-primary" id="wl-add-btn">Add</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Watchlist items -->
  <div class="card" id="watchlist-list">
    <div id="watchlist-items" style="min-height:40px">
      <p style="color:#999;font-size:14px" id="wl-empty">Loading watchlist...</p>
    </div>
  </div>
</div>

<!-- SOURCES -->
<div id="page-sources" class="page">
  <div style="margin-bottom:20px">
    <h2 style="font-size:18px;font-weight:600;margin-bottom:4px">URL Sources</h2>
    <p class="meta" style="margin:0">Paste any product URL to track its price on every scraper run.</p>
  </div>

  <div class="card">
    <h3 style="font-size:14px;font-weight:600;margin-bottom:14px">Add URL source</h3>
    <div style="display:grid;grid-template-columns:1fr 2fr auto;gap:12px;align-items:end">
      <div>
        <div class="setting-label">Label</div>
        <input type="text" id="src-label" placeholder="e.g. eBay Gold Dice Set">
      </div>
      <div>
        <div class="setting-label">Product URL</div>
        <input type="text" id="src-url" placeholder="https://...">
      </div>
      <div>
        <button class="btn btn-primary" id="src-add-btn">Add</button>
      </div>
    </div>
  </div>

  <div class="card">
    <div id="sources-items" style="min-height:40px">
      <p style="color:#999;font-size:14px">Loading sources...</p>
    </div>
  </div>
</div>

<!-- SETTINGS -->
<div id="page-settings" class="page">
  <div style="margin-bottom:20px">
    <h2 style="font-size:18px;font-weight:600">Settings</h2>
  </div>
  <div class="card" id="settings-card">
    <form id="settings-form">
      <div class="setting-row">
        <div class="setting-label">Search keywords</div>
        <div class="setting-desc">Comma-separated keyword phrases for the default dice search</div>
        <textarea id="s-keywords" rows="3"></textarea>
      </div>
      <div class="setting-row">
        <div class="setting-label">Max price (USD)</div>
        <div class="setting-desc">Maximum price for default dice search results</div>
        <input type="number" id="s-maxprice" style="width:150px">
      </div>
      <div class="setting-row">
        <div class="setting-label">Min size (mm)</div>
        <div class="setting-desc">Minimum die size in millimeters</div>
        <input type="number" id="s-minsize" style="width:150px">
      </div>
      <hr class="divider">
      <h3 style="font-size:15px;font-weight:600;margin-bottom:4px">Email alerts</h3>
      <div class="setting-row">
        <div class="setting-label">Alert sender email</div>
        <div class="setting-desc">Gmail address alerts are sent from</div>
        <input type="text" id="s-alert-from" placeholder="you@gmail.com">
      </div>
      <div class="setting-row">
        <div class="setting-label">Gmail app password</div>
        <div class="setting-desc">16-char app password from Google Account &rarr; Security &rarr; App Passwords</div>
        <input type="password" id="s-alert-pw" placeholder="xxxx xxxx xxxx xxxx">
      </div>
      <div class="setting-row">
        <div class="setting-label">Alert recipient email</div>
        <div class="setting-desc">Email address to receive alerts</div>
        <input type="text" id="s-alert-to" placeholder="recipient@example.com">
      </div>
      <div style="margin-top:18px;display:flex;gap:10px;align-items:center">
        <button type="submit" class="btn btn-primary">Save settings</button>
      </div>
      <div style="margin-top:14px">
        <a id="advanced-toggle" style="font-size:13px;color:#888;cursor:pointer;text-decoration:underline">Advanced settings</a>
      </div>
      <div id="advanced-section" style="display:none">
        <hr class="divider">
        <div class="setting-row">
          <div class="setting-label">GitHub Personal Access Token</div>
          <div class="setting-desc">
            Required for the "Run search now" button. Create a token at GitHub &rarr; Settings &rarr; Developer settings &rarr; Personal access tokens with <strong>workflow</strong> scope only.
            Stored in Supabase settings table &mdash; not hardcoded anywhere.
          </div>
          <input type="password" id="s-github-pat" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx">
        </div>
      </div>
    </form>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const SB_URL = "{supabase_url}";
const SB_KEY = "{supabase_key}";
const GH_REPO = "{github_repo}";
const GH_WORKFLOW = "{github_workflow}";

// Plain fetch wrappers — no SDK dependency
async function sbSelect(table, filter="") {{
  const r = await fetch(`${{SB_URL}}/rest/v1/${{table}}?select=*${{filter ? '&' + filter : ''}}`, {{
    headers: {{"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY}}
  }});
  return r.json();
}}

async function sbUpsert(table, data) {{
  await fetch(`${{SB_URL}}/rest/v1/${{table}}`, {{
    method: "POST",
    headers: {{"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
              "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}},
    body: JSON.stringify(data)
  }});
}}

async function sbInsert(table, data) {{
  const r = await fetch(`${{SB_URL}}/rest/v1/${{table}}`, {{
    method: "POST",
    headers: {{"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
              "Content-Type": "application/json", "Prefer": "return=representation"}},
    body: JSON.stringify(data)
  }});
  return r.json();
}}

async function sbUpdate(table, data, filter) {{
  await fetch(`${{SB_URL}}/rest/v1/${{table}}?${{filter}}`, {{
    method: "PATCH",
    headers: {{"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
              "Content-Type": "application/json"}},
    body: JSON.stringify(data)
  }});
}}

async function sbDelete(table, filter) {{
  await fetch(`${{SB_URL}}/rest/v1/${{table}}?${{filter}}`, {{
    method: "DELETE",
    headers: {{"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY}}
  }});
}}

// --- Tab navigation ---
function show(page, el) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav a').forEach(a => a.classList.remove('active'));
  const pageEl = document.getElementById('page-' + page);
  if (pageEl) pageEl.classList.add('active');
  if (el) el.classList.add('active');
  if (page === 'settings') loadSettings();
  if (page === 'watchlist') loadWatchlist();
  if (page === 'sources') loadSources();
}}

// --- Toast ---
function toast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}}

// --- Run search now (GitHub Actions dispatch) ---
async function runNow(btn) {{
  btn.disabled = true;
  btn.innerHTML = '<span class="run-status running">Triggering...</span>';
  try {{
    const pat = await sbSelect('settings', 'key=eq.github_pat').then(d => d[0]?.value);
    if (!pat) {{
      toast('Set your GitHub PAT in Settings first');
      btn.disabled = false;
      btn.innerHTML = '<span>&#9654;</span> Run search now';
      return;
    }}
    const resp = await fetch(
      'https://api.github.com/repos/' + GH_REPO + '/actions/workflows/' + GH_WORKFLOW + '/dispatches',
      {{
        method: 'POST',
        headers: {{
          'Authorization': 'Bearer ' + pat,
          'Accept': 'application/vnd.github.v3+json'
        }},
        body: JSON.stringify({{ ref: 'main' }})
      }}
    );
    if (resp.status === 204) {{
      toast('Search triggered! Results will update in a few minutes.');
      btn.innerHTML = '<span class="run-status">Triggered</span>';
    }} else {{
      const err = await resp.json().catch(() => ({{}}));
      toast('Failed: ' + (err.message || resp.status));
      btn.innerHTML = '<span>&#9654;</span> Run search now';
      btn.disabled = false;
    }}
  }} catch (e) {{
    toast('Error: ' + e.message);
    btn.innerHTML = '<span>&#9654;</span> Run search now';
    btn.disabled = false;
  }}
  setTimeout(() => {{ btn.disabled = false; btn.innerHTML = '<span>&#9654;</span> Run search now'; }}, 10000);
}}

// --- Settings ---
async function loadSettings() {{
  const data = await sbSelect('settings');
  const s = {{}};
  (data || []).forEach(r => s[r.key] = r.value);
  document.getElementById('s-keywords').value = s.search_keywords || '';
  document.getElementById('s-maxprice').value = s.max_price_usd || '150';
  document.getElementById('s-minsize').value = s.min_size_mm || '50';
  document.getElementById('s-github-pat').value = s.github_pat || '';
  document.getElementById('s-alert-from').value = s.alert_from_email || '';
  document.getElementById('s-alert-pw').value = s.alert_gmail_password || '';
  document.getElementById('s-alert-to').value = s.alert_to_email || '';
}}

async function saveSettings(e) {{
  e.preventDefault();
  const pairs = [
    ['search_keywords',      document.getElementById('s-keywords').value],
    ['max_price_usd',        document.getElementById('s-maxprice').value],
    ['min_size_mm',          document.getElementById('s-minsize').value],
    ['github_pat',           document.getElementById('s-github-pat').value],
    ['alert_from_email',     document.getElementById('s-alert-from').value],
    ['alert_gmail_password', document.getElementById('s-alert-pw').value],
    ['alert_to_email',       document.getElementById('s-alert-to').value],
  ];
  await sbUpsert('settings', pairs.map(([key,value]) => ({{key, value}})));
  toast('Settings saved');
}}

// --- Watchlist ---
async function loadWatchlist() {{
  const data = await sbSelect('watchlist', 'order=created_at.asc');
  renderWatchlist(data || []);
}}

function renderWatchlist(items) {{
  const container = document.getElementById('watchlist-items');
  container.innerHTML = '';
  if (!items.length) {{
    container.innerHTML = '<p style="color:#999;font-size:14px">No watchlist items yet. Add one above.</p>';
    return;
  }}
  items.forEach(function(item) {{
    const active = item.is_active !== false;
    const kw = (item.keywords || '').split('\\n').filter(Boolean).join(', ');
    const price = item.max_price ? '$' + Number(item.max_price).toFixed(0) : 'No limit';

    const row = document.createElement('div');
    row.className = 'watchlist-item';

    const nameDiv = document.createElement('div');
    nameDiv.className = 'watchlist-name';
    nameDiv.textContent = item.name;
    if (!active) {{
      const badge = document.createElement('span');
      badge.style.cssText = 'color:#999;font-size:11px';
      badge.textContent = ' (paused)';
      nameDiv.appendChild(badge);
    }}

    const kwDiv = document.createElement('div');
    kwDiv.className = 'watchlist-keywords';
    kwDiv.textContent = kw;

    const priceDiv = document.createElement('div');
    priceDiv.className = 'watchlist-price';
    priceDiv.textContent = price;

    var editBtn = document.createElement('button');
    editBtn.className = 'btn btn-secondary';
    editBtn.style.cssText = 'padding:5px 12px;font-size:12px';
    editBtn.textContent = 'Edit';
    editBtn.addEventListener('click', function() {{
      // Replace row content with inline edit form
      row.innerHTML = '';
      row.style.cssText = 'display:flex;flex-direction:column;gap:10px;padding:12px 0;border-bottom:1px solid #f0f0f0';

      var nameInput = document.createElement('input');
      nameInput.type = 'text';
      nameInput.value = item.name;
      nameInput.style.cssText = 'width:100%;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px';

      var kwInput = document.createElement('textarea');
      kwInput.rows = 3;
      kwInput.value = (item.keywords || '').replace(/\\\\n/g, '\\n');
      kwInput.style.cssText = 'width:100%;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;font-family:inherit';

      var priceInput = document.createElement('input');
      priceInput.type = 'number';
      priceInput.value = item.max_price || '';
      priceInput.placeholder = 'Max price (optional)';
      priceInput.style.cssText = 'width:120px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px';

      var nameLabel = document.createElement('div');
      nameLabel.style.cssText = 'font-size:12px;color:#888;margin-bottom:2px';
      nameLabel.textContent = 'Name';
      var kwLabel = document.createElement('div');
      kwLabel.style.cssText = 'font-size:12px;color:#888;margin-bottom:2px';
      kwLabel.textContent = 'Keywords (one per line)';
      var priceLabel = document.createElement('div');
      priceLabel.style.cssText = 'font-size:12px;color:#888;margin-bottom:2px';
      priceLabel.textContent = 'Max price (USD)';

      var nameGroup = document.createElement('div');
      nameGroup.appendChild(nameLabel);
      nameGroup.appendChild(nameInput);
      var kwGroup = document.createElement('div');
      kwGroup.appendChild(kwLabel);
      kwGroup.appendChild(kwInput);
      var priceGroup = document.createElement('div');
      priceGroup.appendChild(priceLabel);
      priceGroup.appendChild(priceInput);

      var btnRow = document.createElement('div');
      btnRow.style.cssText = 'display:flex;gap:8px';

      var saveBtn = document.createElement('button');
      saveBtn.className = 'btn btn-primary';
      saveBtn.style.cssText = 'padding:5px 16px;font-size:12px';
      saveBtn.textContent = 'Save';
      saveBtn.addEventListener('click', async function() {{
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
        await sbUpdate('watchlist', {{
          name: nameInput.value.trim(),
          keywords: kwInput.value.trim(),
          max_price: priceInput.value || null
        }}, 'id=eq.' + item.id);
        toast('Updated');
        loadWatchlist();
      }});

      var cancelBtn = document.createElement('button');
      cancelBtn.className = 'btn btn-secondary';
      cancelBtn.style.cssText = 'padding:5px 16px;font-size:12px';
      cancelBtn.textContent = 'Cancel';
      cancelBtn.addEventListener('click', function() {{ loadWatchlist(); }});

      btnRow.appendChild(saveBtn);
      btnRow.appendChild(cancelBtn);

      row.appendChild(nameGroup);
      row.appendChild(kwGroup);
      row.appendChild(priceGroup);
      row.appendChild(btnRow);
    }});

    var toggleBtn = document.createElement('button');
    toggleBtn.className = 'btn btn-secondary';
    toggleBtn.style.cssText = 'padding:5px 12px;font-size:12px';
    toggleBtn.textContent = active ? 'Pause' : 'Resume';
    toggleBtn.addEventListener('click', function() {{ toggleWatchlist(item.id, active); }});

    var delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger';
    delBtn.style.cssText = 'padding:5px 12px;font-size:12px';
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', function() {{ deleteWatchlist(item.id); }});

    row.appendChild(nameDiv);
    row.appendChild(kwDiv);
    row.appendChild(priceDiv);
    row.appendChild(editBtn);
    row.appendChild(toggleBtn);
    row.appendChild(delBtn);
    container.appendChild(row);
  }});
}}

function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}

async function addWatchlistItem() {{
  const name = document.getElementById('wl-name').value.trim();
  const keywords = document.getElementById('wl-keywords').value.trim();
  const maxPrice = document.getElementById('wl-maxprice').value;
  if (!name || !keywords) {{ toast('Name and keywords are required'); return; }}
  const row = {{ name, keywords, max_price: maxPrice || null, is_active: true }};
  await sbInsert('watchlist', row);
  document.getElementById('wl-name').value = '';
  document.getElementById('wl-keywords').value = '';
  document.getElementById('wl-maxprice').value = '';
  toast('Added "' + name + '" to watchlist');
  loadWatchlist();
}}

async function deleteWatchlist(id) {{
  if (!confirm('Delete this watchlist item?')) return;
  await sbDelete('watchlist', 'id=eq.' + id);
  toast('Deleted');
  loadWatchlist();
}}

async function toggleWatchlist(id, currentlyActive) {{
  await sbUpdate('watchlist', {{ is_active: !currentlyActive }}, 'id=eq.' + id);
  loadWatchlist();
}}

// --- Sources (URL watcher) ---
async function loadSources() {{
  var data = await sbSelect('url_sources', 'order=created_at.asc');
  renderSources(data || []);
}}

function renderSources(items) {{
  var container = document.getElementById('sources-items');
  container.innerHTML = '';
  if (!items.length) {{
    container.innerHTML = '<p style="color:#999;font-size:14px">No URL sources yet. Add one above.</p>';
    return;
  }}
  items.forEach(function(item) {{
    var active = item.is_active !== false;
    var row = document.createElement('div');
    row.className = 'watchlist-item';

    var labelDiv = document.createElement('div');
    labelDiv.className = 'watchlist-name';
    labelDiv.textContent = item.label;
    if (!active) {{
      var badge = document.createElement('span');
      badge.style.cssText = 'color:#999;font-size:11px';
      badge.textContent = ' (paused)';
      labelDiv.appendChild(badge);
    }}

    var urlDiv = document.createElement('div');
    urlDiv.className = 'watchlist-keywords';
    var urlLink = document.createElement('a');
    urlLink.href = item.url;
    urlLink.target = '_blank';
    urlLink.textContent = item.url.length > 60 ? item.url.substring(0, 60) + '...' : item.url;
    urlDiv.appendChild(urlLink);

    var editBtn = document.createElement('button');
    editBtn.className = 'btn btn-secondary';
    editBtn.style.cssText = 'padding:5px 12px;font-size:12px';
    editBtn.textContent = 'Edit';
    editBtn.addEventListener('click', function() {{
      row.innerHTML = '';
      row.style.cssText = 'display:flex;flex-direction:column;gap:10px;padding:12px 0;border-bottom:1px solid #f0f0f0';

      var li = document.createElement('input');
      li.type = 'text';
      li.value = item.label;
      li.style.cssText = 'width:100%;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px';

      var ui = document.createElement('input');
      ui.type = 'text';
      ui.value = item.url;
      ui.style.cssText = 'width:100%;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px';

      var ll = document.createElement('div');
      ll.style.cssText = 'font-size:12px;color:#888;margin-bottom:2px';
      ll.textContent = 'Label';
      var ul = document.createElement('div');
      ul.style.cssText = 'font-size:12px;color:#888;margin-bottom:2px';
      ul.textContent = 'URL';

      var lg = document.createElement('div');
      lg.appendChild(ll); lg.appendChild(li);
      var ug = document.createElement('div');
      ug.appendChild(ul); ug.appendChild(ui);

      var br = document.createElement('div');
      br.style.cssText = 'display:flex;gap:8px';

      var sb2 = document.createElement('button');
      sb2.className = 'btn btn-primary';
      sb2.style.cssText = 'padding:5px 16px;font-size:12px';
      sb2.textContent = 'Save';
      sb2.addEventListener('click', async function() {{
        sb2.disabled = true;
        sb2.textContent = 'Saving...';
        await sbUpdate('url_sources', {{
          label: li.value.trim(),
          url: ui.value.trim()
        }}, 'id=eq.' + item.id);
        toast('Updated');
        loadSources();
      }});

      var cb = document.createElement('button');
      cb.className = 'btn btn-secondary';
      cb.style.cssText = 'padding:5px 16px;font-size:12px';
      cb.textContent = 'Cancel';
      cb.addEventListener('click', function() {{ loadSources(); }});

      br.appendChild(sb2);
      br.appendChild(cb);
      row.appendChild(lg);
      row.appendChild(ug);
      row.appendChild(br);
    }});

    var toggleBtn = document.createElement('button');
    toggleBtn.className = 'btn btn-secondary';
    toggleBtn.style.cssText = 'padding:5px 12px;font-size:12px';
    toggleBtn.textContent = active ? 'Pause' : 'Resume';
    toggleBtn.addEventListener('click', function() {{
      sbUpdate('url_sources', {{ is_active: !active }}, 'id=eq.' + item.id).then(loadSources);
    }});

    var delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger';
    delBtn.style.cssText = 'padding:5px 12px;font-size:12px';
    delBtn.textContent = 'Delete';
    delBtn.addEventListener('click', function() {{
      if (!confirm('Delete this source?')) return;
      sbDelete('url_sources', 'id=eq.' + item.id).then(function() {{
        toast('Deleted');
        loadSources();
      }});
    }});

    row.appendChild(labelDiv);
    row.appendChild(urlDiv);
    row.appendChild(editBtn);
    row.appendChild(toggleBtn);
    row.appendChild(delBtn);
    container.appendChild(row);
  }});
}}

async function addSource() {{
  var label = document.getElementById('src-label').value.trim();
  var url = document.getElementById('src-url').value.trim();
  if (!label || !url) {{ toast('Label and URL are required'); return; }}
  await sbInsert('url_sources', {{ label: label, url: url, is_active: true }});
  document.getElementById('src-label').value = '';
  document.getElementById('src-url').value = '';
  toast('Added source');
  loadSources();
}}

// --- Run status indicator ---
async function updateRunStatus() {{
  try {{
    var data = await sbSelect('run_log', 'order=ran_at.desc&limit=1');
    var el = document.getElementById('run-status-indicator');
    if (data && data.length && data[0].ran_at) {{
      var ranAt = new Date(data[0].ran_at);
      var now = new Date();
      var diffMin = Math.round((now - ranAt) / 60000);
      if (diffMin < 5) {{
        el.innerHTML = '<span class="pulse-dot"></span>Searching...';
      }} else if (diffMin < 60) {{
        el.textContent = 'Last run: ' + diffMin + ' min ago';
      }} else if (diffMin < 1440) {{
        el.textContent = 'Last run: ' + Math.round(diffMin / 60) + 'h ago';
      }} else {{
        el.textContent = 'Last run: ' + Math.round(diffMin / 1440) + 'd ago';
      }}
    }}
  }} catch (e) {{}}
}}

// --- Init: wire up all events (no inline handlers) ---
document.querySelectorAll('.nav a[data-page]').forEach(function(link) {{
  link.addEventListener('click', function() {{ show(link.dataset.page, link); }});
}});
document.getElementById('header-run-btn').addEventListener('click', function() {{
  runNow(document.getElementById('header-run-btn'));
}});
document.getElementById('wl-add-btn').addEventListener('click', addWatchlistItem);
document.getElementById('src-add-btn').addEventListener('click', addSource);
document.getElementById('settings-form').addEventListener('submit', saveSettings);
document.getElementById('advanced-toggle').addEventListener('click', function() {{
  var sec = document.getElementById('advanced-section');
  sec.style.display = sec.style.display === 'none' ? 'block' : 'none';
}});
// Cache Supabase config for roadmap page
localStorage.setItem("sb_url", SB_URL);
localStorage.setItem("sb_key", SB_KEY);
loadSettings();
loadWatchlist();
updateRunStatus();
setInterval(updateRunStatus, 60000);
</script>
</body>
</html>'''


if __name__ == "__main__":
    generate_dashboard()
