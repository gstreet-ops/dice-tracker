"""
analytics_generate.py - Generates a static analytics.html page.
Called from scrapers/run.py alongside generate_dashboard().
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base import get_supabase
from datetime import datetime, timezone
import logging

logger = logging.getLogger("analytics")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "analytics.html")


def generate_analytics():
    sb = get_supabase()
    products = _fetch_all_products(sb)
    recent_hist = _fetch_recent_history(sb, 50)
    all_hist = _fetch_all_history(sb, products)
    html = _render(products, recent_hist, all_hist)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Analytics page written ({len(products)} products)")


def _fetch_all_products(sb):
    r = sb.table("products").select(
        "id, title, url, source, score, first_seen, last_seen, is_excluded"
    ).eq("is_excluded", False).order("score", desc=True).limit(200).execute()
    return r.data or []


def _fetch_recent_history(sb, limit):
    r = sb.table("price_history").select(
        "product_id, price_usd, in_stock, scraped_at"
    ).order("scraped_at", desc=True).limit(limit).execute()
    return r.data or []


def _fetch_all_history(sb, products):
    grouped = {}
    for p in products:
        r = sb.table("price_history").select(
            "price_usd, in_stock, scraped_at"
        ).eq("product_id", p["id"]).order("scraped_at", desc=True).limit(200).execute()
        grouped[p["id"]] = r.data or []
    return grouped


def _trend(hist):
    if len(hist) < 2:
        return "&#8212;"
    vals = [h["price_usd"] for h in hist[:5]]
    if vals[0] < vals[-1]:
        return '<span style="color:#27ae60">&#9660; Down</span>'
    if vals[0] > vals[-1]:
        return '<span style="color:#e74c3c">&#9650; Up</span>'
    return '<span style="color:#888">&#8212; Stable</span>'


def _stock_pct(hist):
    if not hist:
        return None
    return round(sum(1 for h in hist if h.get("in_stock")) / len(hist) * 100)


def _rel(iso):
    if not iso:
        return "&#8212;"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        d = (datetime.now(timezone.utc) - dt).days
        if d == 0:
            h = int((datetime.now(timezone.utc) - dt).total_seconds() / 3600)
            return "just now" if h == 0 else f"{h}h ago"
        return "yesterday" if d == 1 else f"{d}d ago"
    except Exception:
        return "&#8212;"


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _render(products, recent_hist, all_hist):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    prod_map = {p["id"]: p for p in products}
    total_checks = sum(len(h) for h in all_hist.values())
    total_drops = 0
    for hist in all_hist.values():
        for i in range(len(hist) - 1):
            if hist[i]["price_usd"] < hist[i + 1]["price_usd"]:
                total_drops += 1
    sources_active = len(set(p["source"] for p in products))

    # Price summary rows
    price_rows = ""
    for p in products:
        hist = all_hist.get(p["id"], [])
        if not hist:
            continue
        cur = hist[0]["price_usd"]
        prices = [h["price_usd"] for h in hist]
        atl = min(prices)
        cutoff = datetime.now(timezone.utc).timestamp() - 7 * 86400
        r7 = []
        for h in hist:
            try:
                ts = datetime.fromisoformat(h["scraped_at"].replace("Z", "+00:00")).timestamp()
                if ts >= cutoff:
                    r7.append(h["price_usd"])
            except Exception:
                pass
        l7 = min(r7) if r7 else cur
        h7 = max(r7) if r7 else cur
        sc = p.get("score", 0)
        sc_color = "#27ae60" if sc >= 70 else "#f39c12" if sc >= 40 else "#e74c3c"
        t = _esc(p["title"] or "")[:55]
        price_rows += (
            '<tr>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;font-size:13px">'
            f'<a href="{_esc(p["url"])}" target="_blank" style="color:#0066cc;text-decoration:none">{t}</a>'
            f'<br><span style="font-size:11px;color:#aaa">{_esc(p["source"])}</span></td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;font-weight:600;color:{sc_color}">{sc}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;font-weight:500">${cur:.2f}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;color:#888">${l7:.2f}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;color:#888">${h7:.2f}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;color:#888">${atl:.2f}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center">{_trend(hist)}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;font-size:12px;color:#aaa">{len(hist)}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;font-size:12px;color:#aaa">{_rel(p.get("first_seen"))}</td>'
            '</tr>'
        )

    # Stock bars
    stock_bars = ""
    for p in products:
        hist = all_hist.get(p["id"], [])
        if len(hist) < 3:
            continue
        pct = _stock_pct(hist)
        if pct is None:
            continue
        bc = "#27ae60" if pct >= 70 else "#f39c12" if pct >= 30 else "#e74c3c"
        t = _esc(p["title"] or "")[:45]
        stock_bars += (
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            f'<div style="width:200px;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{t}</div>'
            f'<div style="flex:1;background:#f0f0f0;border-radius:4px;height:18px;overflow:hidden">'
            f'<div style="width:{pct}%;background:{bc};height:100%;border-radius:4px"></div></div>'
            f'<div style="width:45px;text-align:right;font-size:12px;color:#888">{pct}%</div></div>'
        )

    # Score distribution
    strong = sum(1 for p in products if p.get("score", 0) >= 70)
    partial = sum(1 for p in products if 40 <= p.get("score", 0) < 70)
    weak = sum(1 for p in products if p.get("score", 0) < 40)
    total_scored = len(products)

    # Source breakdown
    src = {}
    for p in products:
        s = p["source"]
        if s not in src:
            src[s] = {"count": 0, "prices": [], "scores": []}
        src[s]["count"] += 1
        src[s]["scores"].append(p.get("score", 0))
        hist = all_hist.get(p["id"], [])
        if hist:
            src[s]["prices"].append(hist[0]["price_usd"])
    source_rows = ""
    for s, d in sorted(src.items(), key=lambda x: -x[1]["count"]):
        avg = sum(d["prices"]) / len(d["prices"]) if d["prices"] else 0
        avg_score = round(sum(d["scores"]) / len(d["scores"])) if d["scores"] else 0
        sc_color = "#27ae60" if avg_score >= 70 else "#f39c12" if avg_score >= 40 else "#e74c3c"
        source_rows += (
            f'<tr><td style="padding:8px;border-bottom:1px solid #eee;font-weight:500">{_esc(s)}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center">{d["count"]}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right">${avg:.2f}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;font-weight:600;color:{sc_color}">{avg_score}</td></tr>'
        )

    # Recent history
    hist_rows = ""
    for h in recent_hist:
        pr = prod_map.get(h.get("product_id", ""), {})
        t = _esc(pr.get("title") or h.get("product_id", ""))[:50]
        sc = "#27ae60" if h.get("in_stock") else "#e74c3c"
        sl = "In stock" if h.get("in_stock") else "Out"
        hist_rows += (
            f'<tr><td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:12px">{t}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;font-size:12px">${h["price_usd"]:.2f}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center;font-size:12px;color:{sc}">{sl}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center;font-size:12px;color:#aaa">{_rel(h.get("scraped_at"))}</td></tr>'
        )

    no_stock = '<p style="color:#999;font-size:13px">Not enough data yet.</p>' if not stock_bars else stock_bars

    CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f7f7f7;color:#1a1a1a}
.header{background:#fff;border-bottom:1px solid #e5e5e5;padding:0 24px;display:flex;align-items:center;gap:24px}
.header h1{font-size:18px;font-weight:600;padding:16px 0}
.header a{font-size:13px;color:#888;text-decoration:none;margin-left:auto}
.header a:hover{color:#1a1a1a}
.content{max-width:1000px;margin:0 auto;padding:28px 24px}
.card{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:20px 24px;margin-bottom:16px}
.card h3{font-size:14px;font-weight:600;margin-bottom:14px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
.stat{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:16px 20px}
.stat-val{font-size:28px;font-weight:600}
.stat-lbl{font-size:12px;color:#888;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{background:#fafafa;padding:8px;text-align:left;font-weight:500;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #eee}
.meta{color:#999;font-size:13px;margin-bottom:20px}"""

    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Product Tracker - Analytics</title>'
        f'<style>{CSS}</style></head><body>'
        '<div class="header"><h1>Analytics</h1><a href="index.html">&larr; Back to dashboard</a></div>'
        '<div class="content">'
        f'<p class="meta">Generated: {now}</p>'
        '<div class="stats">'
        f'<div class="stat"><div class="stat-val">{len(products)}</div><div class="stat-lbl">Products tracked</div></div>'
        f'<div class="stat"><div class="stat-val">{total_checks}</div><div class="stat-lbl">Total price checks</div></div>'
        f'<div class="stat"><div class="stat-val">{total_drops}</div><div class="stat-lbl">Price drops detected</div></div>'
        f'<div class="stat"><div class="stat-val">{sources_active}</div><div class="stat-lbl">Sources active</div></div>'
        '</div>'
        '<div class="card"><h3>Match score distribution</h3>'
        '<p style="font-size:12px;color:#888;margin-bottom:14px">How well do tracked products match the target criteria? Score 70+ = strong, 40–69 = partial, below 40 = weak.</p>'
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">'
        f'<div style="background:#e8f5e9;border-radius:8px;padding:16px;text-align:center">'
        f'<div style="font-size:28px;font-weight:600;color:#27ae60">{strong}</div>'
        f'<div style="font-size:12px;color:#27ae60;margin-top:4px">Strong match (70+)</div>'
        f'<div style="font-size:11px;color:#888;margin-top:2px">{round(strong/total_scored*100) if total_scored else 0}% of total</div></div>'
        f'<div style="background:#fff8e1;border-radius:8px;padding:16px;text-align:center">'
        f'<div style="font-size:28px;font-weight:600;color:#f39c12">{partial}</div>'
        f'<div style="font-size:12px;color:#f39c12;margin-top:4px">Partial match (40–69)</div>'
        f'<div style="font-size:11px;color:#888;margin-top:2px">{round(partial/total_scored*100) if total_scored else 0}% of total</div></div>'
        f'<div style="background:#fef5f5;border-radius:8px;padding:16px;text-align:center">'
        f'<div style="font-size:28px;font-weight:600;color:#e74c3c">{weak}</div>'
        f'<div style="font-size:12px;color:#e74c3c;margin-top:4px">Weak match (below 40)</div>'
        f'<div style="font-size:11px;color:#888;margin-top:2px">{round(weak/total_scored*100) if total_scored else 0}% of total</div></div>'
        '</div></div>'
        '<div class="card"><h3>Price summary</h3>'
        '<table><thead><tr>'
        '<th>Product</th><th style="text-align:center">Score</th><th style="text-align:right">Current</th><th style="text-align:right">7d low</th>'
        '<th style="text-align:right">7d high</th><th style="text-align:right">All-time low</th>'
        '<th style="text-align:center">Trend</th><th style="text-align:center">Points</th><th style="text-align:center">First seen</th>'
        f'</tr></thead><tbody>{price_rows}</tbody></table></div>'
        '<div class="card"><h3>Stock availability</h3>'
        '<p style="font-size:12px;color:#888;margin-bottom:12px">Products with 3+ data points. Bar shows % of checks where item was in stock.</p>'
        f'{no_stock}</div>'
        '<div class="card"><h3>Source breakdown</h3>'
        '<table><thead><tr><th>Source</th><th style="text-align:center">Products</th><th style="text-align:right">Avg price</th><th style="text-align:center">Avg score</th></tr></thead>'
        f'<tbody>{source_rows}</tbody></table></div>'
        '<div class="card"><h3>Recent price history</h3>'
        '<p style="font-size:12px;color:#888;margin-bottom:10px">Last 50 price checks across all products.</p>'
        '<table><thead><tr><th>Product</th><th style="text-align:right">Price</th><th style="text-align:center">Stock</th><th style="text-align:center">When</th></tr></thead>'
        f'<tbody>{hist_rows}</tbody></table></div>'
        '</div></body></html>'
    )


if __name__ == "__main__":
    generate_analytics()
