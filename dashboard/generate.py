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
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
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
    a{{color:#0066cc}}
    .divider{{border:none;border-top:1px solid #f0f0f0;margin:20px 0}}
  </style>
</head>
<body>
<div class="header">
  <h1>Product Tracker</h1>
  <nav class="nav">
    <a class="active" id="nav-results" onclick="show('results',this)">Results</a>
    <a id="nav-watchlist" onclick="show('watchlist',this)">Watchlist</a>
    <a id="nav-settings" onclick="show('settings',this)">Settings</a>
  </nav>
</div>

<!-- RESULTS -->
<div id="page-results" class="page active">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
    <p class="meta" style="margin:0">Last updated: {now} &nbsp;&middot;&nbsp; Last search: {last_run}</p>
    <button class="btn btn-green" onclick="runNow(this)">
      <span>&#9654;</span> Run search now
    </button>
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
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:20px;font-size:12px;color:#bbb">Score: 70+ = strong &nbsp;&middot;&nbsp; 40&ndash;69 = partial &nbsp;&middot;&nbsp; below 40 = weak</p>
  </div>
</div>

<!-- WATCHLIST -->
<div id="page-watchlist" class="page">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
    <div>
      <h2 style="font-size:18px;font-weight:600;margin-bottom:4px">Watchlist</h2>
      <p class="meta" style="margin:0">Add product categories to search for. Each item runs as a separate search.</p>
    </div>
    <button class="btn btn-green" onclick="runNow(this)">
      <span>&#9654;</span> Run search now
    </button>
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
          <button class="btn btn-primary" onclick="addWatchlistItem()">Add</button>
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

<!-- SETTINGS -->
<div id="page-settings" class="page">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
    <h2 style="font-size:18px;font-weight:600">Settings</h2>
    <button class="btn btn-green" onclick="runNow(this)">
      <span>&#9654;</span> Run search now
    </button>
  </div>
  <div class="card" id="settings-card">
    <form onsubmit="saveSettings(event)">
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
      <div class="setting-row">
        <div class="setting-label">GitHub Personal Access Token</div>
        <div class="setting-desc">
          Required for the "Run search now" button. Create a token at GitHub &rarr; Settings &rarr; Developer settings &rarr; Personal access tokens with <strong>workflow</strong> scope only.
          Stored in Supabase settings table &mdash; not hardcoded anywhere.
        </div>
        <input type="password" id="s-github-pat" placeholder="ghp_xxxxxxxxxxxxxxxxxxxx">
      </div>
      <div style="margin-top:18px;display:flex;gap:10px">
        <button type="submit" class="btn btn-primary">Save settings</button>
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

let sb;
function getSB() {{
  if (!sb) {{
    if (!window.supabase) {{ toast('Supabase not loaded yet — try again'); return null; }}
    sb = window.supabase.createClient(SB_URL, SB_KEY);
  }}
  return sb;
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
    const {{ data }} = await getSB().from('settings').select('value').eq('key', 'github_pat').single();
    const pat = data && data.value;
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
  const {{ data }} = await getSB().from('settings').select('key, value');
  const s = {{}};
  (data || []).forEach(r => s[r.key] = r.value);
  document.getElementById('s-keywords').value = s.search_keywords || '';
  document.getElementById('s-maxprice').value = s.max_price_usd || '150';
  document.getElementById('s-minsize').value = s.min_size_mm || '50';
  document.getElementById('s-github-pat').value = s.github_pat || '';
}}

async function saveSettings(e) {{
  e.preventDefault();
  const pairs = [
    ['search_keywords', document.getElementById('s-keywords').value],
    ['max_price_usd', document.getElementById('s-maxprice').value],
    ['min_size_mm', document.getElementById('s-minsize').value],
    ['github_pat', document.getElementById('s-github-pat').value],
  ];
  for (const [key, value] of pairs) {{
    await getSB().from('settings').upsert({{ key, value }}, {{ onConflict: 'key' }});
  }}
  toast('Settings saved');
}}

// --- Watchlist ---
async function loadWatchlist() {{
  const {{ data, error }} = await getSB().from('watchlist').select('*').order('created_at', {{ ascending: true }});
  renderWatchlist(data || []);
}}

function renderWatchlist(items) {{
  const container = document.getElementById('watchlist-items');
  if (!items.length) {{
    container.innerHTML = '<p style="color:#999;font-size:14px">No watchlist items yet. Add one above.</p>';
    return;
  }}
  container.innerHTML = items.map(item => {{
    const kw = (item.keywords || '').split('\\n').filter(Boolean).join(', ');
    const price = item.max_price ? '$' + Number(item.max_price).toFixed(0) : 'No limit';
    const active = item.is_active !== false;
    return '<div class="watchlist-item">' +
      '<div class="watchlist-name">' + esc(item.name) + (active ? '' : ' <span style="color:#999;font-size:11px">(paused)</span>') + '</div>' +
      '<div class="watchlist-keywords">' + esc(kw) + '</div>' +
      '<div class="watchlist-price">' + price + '</div>' +
      '<button class="btn btn-secondary" style="padding:5px 12px;font-size:12px" onclick="toggleWatchlist(\'' + item.id + '\',' + active + ')">' + (active ? 'Pause' : 'Resume') + '</button>' +
      '<button class="btn btn-danger" style="padding:5px 12px;font-size:12px" onclick="deleteWatchlist(\'' + item.id + '\')">Delete</button>' +
    '</div>';
  }}).join('');
}}

function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}

async function addWatchlistItem() {{
  const name = document.getElementById('wl-name').value.trim();
  const keywords = document.getElementById('wl-keywords').value.trim();
  const maxPrice = document.getElementById('wl-maxprice').value;
  if (!name || !keywords) {{ toast('Name and keywords are required'); return; }}
  const row = {{ name, keywords, max_price: maxPrice || null, is_active: true }};
  const {{ error }} = await getSB().from('watchlist').insert(row);
  if (error) {{ toast('Error: ' + error.message); return; }}
  document.getElementById('wl-name').value = '';
  document.getElementById('wl-keywords').value = '';
  document.getElementById('wl-maxprice').value = '';
  toast('Added "' + name + '" to watchlist');
  loadWatchlist();
}}

async function deleteWatchlist(id) {{
  if (!confirm('Delete this watchlist item?')) return;
  await getSB().from('watchlist').delete().eq('id', id);
  toast('Deleted');
  loadWatchlist();
}}

async function toggleWatchlist(id, currentlyActive) {{
  await getSB().from('watchlist').update({{ is_active: !currentlyActive }}).eq('id', id);
  loadWatchlist();
}}

// --- Init ---
loadSettings();
loadWatchlist();
</script>
</body>
</html>'''


if __name__ == "__main__":
    generate_dashboard()
