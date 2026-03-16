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


def generate_dashboard():
    sb = get_supabase()
    products = _fetch_products(sb)
    run_stats = _fetch_run_stats(sb)
    html = _render(products, run_stats)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Dashboard written to {OUTPUT_PATH} ({len(products)} products)")


def _fetch_products(sb) -> list[dict]:
    result = (
        sb.table("products")
        .select("id, title, url, source, score, size_mm, finish, material, pip_style, last_seen, is_excluded")
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


def _fetch_run_stats(sb) -> dict:
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


def _render(products: list[dict], stats: dict) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    last_run = stats.get("ran_at", "unknown")[:16].replace("T", " ") if stats.get("ran_at") else "unknown"
    total = len(products)
    in_stock = sum(1 for p in products if p.get("in_stock"))

    rows = ""
    for p in products:
        score = p.get("score", 0)
        score_color = "#27ae60" if score >= 70 else "#f39c12" if score >= 40 else "#e74c3c"
        price = f"${p['price_usd']:.2f}" if p.get("price_usd") else "—"
        stock_badge = (
            '<span style="color:#27ae60;font-weight:500">In stock</span>'
            if p.get("in_stock")
            else '<span style="color:#e74c3c">Out of stock</span>'
        )
        size = f"{p['size_mm']}mm" if p.get("size_mm") else "—"
        rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee">
            <a href="{p['url']}" target="_blank"
               style="color:#0066cc;font-weight:500;text-decoration:none">
              {p['title'][:65]}
            </a><br>
            <span style="font-size:12px;color:#888">{p['source']}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center">{size}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:right;font-weight:500">{price}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center">{stock_badge}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center">
            <span style="color:{score_color};font-weight:600">{score}</span>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>dice-tracker dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           max-width: 1000px; margin: 0 auto; padding: 24px; color: #1a1a1a; }}
    h1 {{ font-size: 22px; margin-bottom: 4px; }}
    .meta {{ color: #888; font-size: 13px; margin-bottom: 24px; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr);
              gap: 12px; margin-bottom: 28px; }}
    .stat {{ background: #f8f8f8; border-radius: 8px; padding: 14px 16px; }}
    .stat-val {{ font-size: 24px; font-weight: 600; }}
    .stat-lbl {{ font-size: 12px; color: #888; margin-top: 2px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th {{ background: #f5f5f5; padding: 10px 8px; text-align: left;
          font-weight: 500; font-size: 12px; color: #555;
          text-transform: uppercase; letter-spacing: .04em; }}
    tr:hover td {{ background: #fafafa; }}
    a {{ color: #0066cc; }}
  </style>
</head>
<body>
  <h1>dice-tracker</h1>
  <p class="meta">Global premium dice tracker · updated {now} · last scrape run {last_run}</p>
  <div class="stats">
    <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Products tracked</div></div>
    <div class="stat"><div class="stat-val">{in_stock}</div><div class="stat-lbl">In stock</div></div>
    <div class="stat"><div class="stat-val">{stats.get('new_products', 0)}</div><div class="stat-lbl">New (last run)</div></div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Product</th>
        <th style="text-align:center">Size</th>
        <th style="text-align:right">Price</th>
        <th style="text-align:center">Stock</th>
        <th style="text-align:center">Score</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="margin-top:32px;font-size:12px;color:#aaa">
    Criteria: ≥50mm · gold body · engraved pips · solid material · set of 2-3
    · Sources: Chessex, eBay, AliExpress, Google Shopping
  </p>
</body>
</html>"""


if __name__ == "__main__":
    generate_dashboard()
