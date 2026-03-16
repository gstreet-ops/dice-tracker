"""
email.py — Gmail SMTP alert sender for dice-tracker.
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger("alerts.email")


def send_alert(new_count: int, drop_count: int, top_products: list[dict]):
    gmail = os.environ.get("GMAIL_ADDRESS", "")
    app_pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    to_email = os.environ.get("ALERT_TO_EMAIL", gmail)

    if not gmail or not app_pw:
        logger.warning("Gmail credentials not set — skipping alert")
        return

    subject = _build_subject(new_count, drop_count)
    html = _build_html(new_count, drop_count, top_products)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, app_pw)
            server.sendmail(gmail, to_email, msg.as_string())
        logger.info(f"Alert sent to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


def _build_subject(new_count: int, drop_count: int) -> str:
    parts = []
    if new_count:
        parts.append(f"{new_count} new product{'s' if new_count > 1 else ''}")
    if drop_count:
        parts.append(f"{drop_count} price drop{'s' if drop_count > 1 else ''}")
    summary = " & ".join(parts) if parts else "Daily summary"
    return f"[dice-tracker] {summary}"


def _build_html(new_count: int, drop_count: int, products: list[dict]) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    rows = ""
    for p in products:
        price = f"${p['price_usd']:.2f}" if p.get("price_usd") else "—"
        stock = "In stock" if p.get("in_stock") else "Out of stock"
        score = p.get("score", 0)
        rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee">
            <a href="{p['url']}" style="color:#0066cc;text-decoration:none">
              {p['title'][:70]}
            </a><br>
            <small style="color:#888">{p['source']} · score {score}/100</small>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">
            <strong>{price}</strong><br>
            <small style="color:#{'27ae60' if p.get('in_stock') else 'e74c3c'}">{stock}</small>
          </td>
        </tr>"""

    return f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#333">
      <h2 style="color:#1a1a1a;border-bottom:2px solid #f0c040;padding-bottom:8px">
        dice-tracker alert
      </h2>
      <p style="color:#666;font-size:14px">{now}</p>
      {"<p><strong>" + str(new_count) + " new products found</strong></p>" if new_count else ""}
      {"<p><strong>" + str(drop_count) + " price drops detected</strong></p>" if drop_count else ""}
      <h3 style="margin-top:24px">Top matches</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead>
          <tr style="background:#f5f5f5">
            <th style="padding:8px;text-align:left">Product</th>
            <th style="padding:8px;text-align:right">Price</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:24px">
        <a href="https://gstreet-ops.github.io/dice-tracker"
           style="background:#f0c040;color:#1a1a1a;padding:10px 20px;
                  text-decoration:none;border-radius:4px;font-weight:bold">
          View full dashboard
        </a>
      </p>
      <p style="color:#aaa;font-size:12px;margin-top:32px">
        dice-tracker · runs every 6 hours via GitHub Actions
      </p>
    </body></html>"""
