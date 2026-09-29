"""Two illustrations of the Kelder domain model: a logical view and an ERD (crow's foot).

    uv run python charts/domain_model.py

Writes charts/out/domain_model_logical.svg and charts/out/domain_model_erd.svg.

This is a DESIGN. Kelder's dbt project has no domain layer yet, and both figures say so. The entities are
the ones in the talk outline (customer, subscription, subscription status change, delivery, payment attempt),
plus the review queue that the "a cancellation needs an initiator and a reason" rule creates.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "charts" / "out"

ESPRESSO, CREMA, BAKSTEEN, GRACHT, HONING = "#2A1C15", "#F4EADB", "#A9462B", "#2F5B55", "#D9A441"
PAPER, LINE, MUTED = "#FAF4E9", "#CDBFA9", "#7A6656"
SERIF = "Fraunces, Georgia, serif"
SANS = "'Instrument Sans', 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, monospace"
HAND = "Caveat, 'Bradley Hand', cursive"

W, H = 1600, 900


def t(x, y, s, size=16, fam=SANS, fill=ESPRESSO, weight=400, anchor="start", style="normal", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-style="{style}"{sp}>{escape(s)}</text>')


def wrap(x, y, lines, size=15, fam=SANS, fill=ESPRESSO, lh=None, **kw):
    lh = lh or size * 1.45
    return "".join(t(x, y + i * lh, ln, size, fam, fill, **kw) for i, ln in enumerate(lines))


def frame(body: str, title: str, subtitle: str, note: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">
<rect width="{W}" height="{H}" fill="{CREMA}"/>
{t(60, 62, title, 34, SERIF, ESPRESSO, 500)}
{t(60, 92, subtitle, 15, MONO, MUTED, spacing=0.4)}
<g transform="translate({W - 60},58)"><rect x="-292" y="-22" width="292" height="34" rx="17" fill="none" stroke="{BAKSTEEN}" stroke-width="1.6"/>
{t(-146, 0, "DESIGN, NOT BUILT ON KELDER", 13, MONO, BAKSTEEN, 500, "middle", spacing=1)}</g>
{body}
{t(60, H - 22, note, 13.5, MONO, MUTED)}
</svg>
'''


# ------------------------------------------------------------------------------------------ logical view


def entity(x, y, w, name, definition, attrs, color=ESPRESSO, dashed=False):
    h = 92 + len(definition) * 21 + len(attrs) * 24
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{PAPER}" stroke="{color}" stroke-width="2.4"{dash}/>'
    s += f'<path d="M{x} {y + 14}a14 14 0 0 1 14 -14h{w - 28}a14 14 0 0 1 14 14v30h-{w}z" fill="{color}"/>'
    s += t(x + 20, y + 32, name, 25, SERIF, CREMA, 600)
    s += wrap(x + 20, y + 72, definition, 15.5, SANS, ESPRESSO, 21)
    ay = y + 72 + len(definition) * 21 + 14
    s += f'<line x1="{x + 20}" x2="{x + w - 20}" y1="{ay - 12}" y2="{ay - 12}" stroke="{LINE}"/>'
    for i, a in enumerate(attrs):
        s += t(x + 20, ay + 10 + i * 24, a, 14, MONO, MUTED if not a.startswith("*") else BAKSTEEN)
    return s, h


def arrow(x1, y1, x2, y2, label=None, lx=None, ly=None, color=ESPRESSO, dashed=False, width=2.4):
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{dash}/>'
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    s += (f'<path d="M{x2} {y2}L{x2 - ux * 16 + px * 8} {y2 - uy * 16 + py * 8}L{x2 - ux * 16 - px * 8} {y2 - uy * 16 - py * 8}Z" fill="{color}"/>')
    if label:
        lx = lx if lx is not None else (x1 + x2) / 2
        ly = ly if ly is not None else (y1 + y2) / 2
        wd = len(label) * 8.6 + 24
        s += f'<rect x="{lx - wd / 2}" y="{ly - 15}" width="{wd}" height="28" rx="14" fill="{CREMA}" stroke="{LINE}"/>'
        s += t(lx, ly + 5, label, 14, MONO, ESPRESSO, 500, "middle")
    return s


def logical() -> str:
    b = ""
    cust, ch = entity(50, 170, 280, "Customer", ["A person who buys from", "Kelder."],
                      ["customer id", "country", "first order channel"])
    sub, sh = entity(450, 170, 320, "Subscription", ["A standing order for coffee.", "Recurring or gift."],
                     ["subscription id", "type: recurring | gift", "product, interval, price", "started at"], color=GRACHT)
    chg, gh = entity(890, 170, 330, "Status change", ["Something that happened to a", "subscription's state."],
                     ["kind: started | paused |", "      resumed | cancelled | expired", "occurred at", "*initiator: customer | dunning | ops", "*reason"], color=BAKSTEEN)
    held, hh = entity(1330, 170, 230, "Held for review", ["Refused by the", "rule. Not churn."],
                      ["source row", "rule broken"], color=BAKSTEEN, dashed=True)
    dev, dh = entity(300, 560, 340, "Delivery", ["A parcel sent for a", "subscription."],
                     ["shipped at, delivered at", "carrier", "failed: yes | no"])
    pay, ph = entity(720, 560, 340, "Payment attempt", ["A try at charging the", "card for a renewal."],
                     ["attempted at", "outcome: paid | failed", "recovered at"])
    b += cust + sub + chg + held + dev + pay

    mid = 170 + 130
    b += arrow(330, mid, 450, mid, "has many", 390, mid - 30)
    b += arrow(770, mid, 890, mid, "records", 830, mid - 30)
    b += arrow(1220, mid, 1330, mid, None, color=BAKSTEEN, dashed=True)
    b += t(1275, mid - 14, "no initiator,", 12.5, MONO, BAKSTEEN, 500, "middle")
    b += t(1275, mid + 32, "no reason", 12.5, MONO, BAKSTEEN, 500, "middle")
    # subscription down to delivery and payment attempt
    b += f'<path d="M610 {170 + sh} V500 H470 V560 M610 500 H890 V560" fill="none" stroke="{ESPRESSO}" stroke-width="2.4"/>'
    for x in (470, 890):
        b += f'<path d="M{x} 560l-8 -16h16z" fill="{ESPRESSO}"/>'
    b += t(540, 486, "is delivered by", 14, MONO, MUTED, 500, "middle")
    b += t(750, 486, "is billed through", 14, MONO, MUTED, 500, "middle")

    # the rule
    b += f'<rect x="1120" y="560" width="450" height="240" rx="14" fill="{ESPRESSO}"/>'
    b += t(1146, 600, "The rule that matters", 26, SERIF, HONING, 600)
    b += wrap(1146, 640, ["A cancellation must have an initiator", "and a reason.", "",
                          "The 12 March import rows have neither,",
                          "so the domain layer refuses to call them",
                          "cancellations and holds them for review.", ], 16.5, SANS, CREMA, 23)
    b += t(60, 800, "A pause is a state, never a cancellation.", 19, HAND, BAKSTEEN, 600)
    b += t(60, 830, "A gift is a type of subscription with no recurring revenue.", 19, HAND, BAKSTEEN, 600)
    return frame(b, "Kelder domain model, logical view",
                 "WHAT KELDER IS MADE OF, BEFORE ANY SOURCE SYSTEM",
                 "Written before looking at any data source. Shopify and Recharge map into this; nothing downstream reads them directly.")


# --------------------------------------------------------------------------------------------- ERD

ROW, HEAD = 30, 46


def table(x, y, w, name, cols, color=ESPRESSO, dashed=False):
    h = HEAD + len(cols) * ROW + 10
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PAPER}" stroke="{color}" stroke-width="2.2"{dash}/>'
    s += f'<path d="M{x} {y + 10}a10 10 0 0 1 10 -10h{w - 20}a10 10 0 0 1 10 10v{HEAD - 10}h-{w}z" fill="{color}"/>'
    s += t(x + 16, y + 30, name, 17.5, MONO, CREMA, 600)
    for i, (key, cname, ctype, emph) in enumerate(cols):
        cy = y + HEAD + 22 + i * ROW
        if i:
            s += f'<line x1="{x + 10}" x2="{x + w - 10}" y1="{cy - 20}" y2="{cy - 20}" stroke="{LINE}" stroke-width="0.8"/>'
        if key:
            s += t(x + 14, cy, key, 12, MONO, HONING if key == "PK" else GRACHT, 700)
        s += t(x + 52, cy, cname, 14.5, MONO, BAKSTEEN if emph else ESPRESSO, 600 if emph else 400)
        s += t(x + w - 14, cy, ctype, 12.5, MONO, MUTED, 400, "end")
    return s, h


def foot_many(x, y, d):
    """Crow's foot with a ring (zero or many) at (x, y); d = ('x'|'y', sign) is the direction into the table."""
    ax, sg = d
    if ax == "x":
        bx = x - sg * 18
        return (f'<path d="M{bx} {y}L{x} {y - 9}M{bx} {y}L{x} {y + 9}M{bx} {y}L{x} {y}" stroke="{ESPRESSO}" stroke-width="2.2" fill="none"/>'
                f'<circle cx="{x - sg * 28}" cy="{y}" r="5.5" fill="{CREMA}" stroke="{ESPRESSO}" stroke-width="2"/>')
    by = y - sg * 18
    return (f'<path d="M{x} {by}L{x - 9} {y}M{x} {by}L{x + 9} {y}M{x} {by}L{x} {y}" stroke="{ESPRESSO}" stroke-width="2.2" fill="none"/>'
            f'<circle cx="{x}" cy="{y - sg * 28}" r="5.5" fill="{CREMA}" stroke="{ESPRESSO}" stroke-width="2"/>')


def foot_one_many(x, y, d):
    ax, sg = d
    if ax == "x":
        bx = x - sg * 18
        return (f'<path d="M{bx} {y}L{x} {y - 9}M{bx} {y}L{x} {y + 9}M{bx} {y}L{x} {y}M{x - sg * 26} {y - 9}v18" stroke="{ESPRESSO}" stroke-width="2.2" fill="none"/>')
    by = y - sg * 18
    return (f'<path d="M{x} {by}L{x - 9} {y}M{x} {by}L{x + 9} {y}M{x} {by}L{x} {y}M{x - 9} {y - sg * 26}h18" stroke="{ESPRESSO}" stroke-width="2.2" fill="none"/>')


def bar_one(x, y, d):
    ax, sg = d
    if ax == "x":
        return f'<path d="M{x - sg * 12} {y - 9}v18M{x - sg * 20} {y - 9}v18" stroke="{ESPRESSO}" stroke-width="2.2"/>'
    return f'<path d="M{x - 9} {y - sg * 12}h18M{x - 9} {y - sg * 20}h18" stroke="{ESPRESSO}" stroke-width="2.2"/>'


def erd() -> str:
    b = ""
    cust, ch = table(60, 150, 330, "domain.customer", [
        ("PK", "customer_id", "bigint", False), ("", "email", "varchar", False), ("", "country_code", "varchar", False),
        ("", "created_at", "timestamptz", False), ("", "first_order_channel", "varchar", False)])
    sub, sh = table(490, 150, 360, "domain.subscription", [
        ("PK", "subscription_id", "bigint", False), ("FK", "customer_id", "bigint", False),
        ("", "subscription_type", "recurring|gift", True), ("", "sku", "varchar", False), ("", "interval_days", "int", False),
        ("", "price_eur", "numeric", False), ("", "started_at", "timestamptz", False), ("", "source_system", "varchar", False)], color=GRACHT)
    chg, gh = table(960, 150, 380, "domain.subscription_status_change", [
        ("PK", "status_change_id", "bigint", False), ("FK", "subscription_id", "bigint", False),
        ("", "kind", "started|paused|...", False), ("", "occurred_at", "timestamptz", False),
        ("", "initiator", "customer|dunning|ops", True), ("", "reason", "varchar", True), ("", "source_system", "varchar", False)], color=BAKSTEEN)
    pay, ph = table(230, 560, 340, "domain.payment_attempt", [
        ("PK", "payment_attempt_id", "bigint", False), ("FK", "subscription_id", "bigint", False),
        ("", "attempted_at", "timestamptz", False), ("", "outcome", "paid|failed", False), ("", "recovered_at", "timestamptz", False)])
    dev, dh = table(640, 560, 340, "domain.delivery", [
        ("PK", "delivery_id", "bigint", False), ("FK", "subscription_id", "bigint", False),
        ("", "shipped_at", "timestamptz", False), ("", "delivered_at", "timestamptz", False),
        ("", "carrier", "varchar", False), ("", "is_failed", "boolean", False)])
    held, hd = table(1050, 560, 380, "domain.held_for_review", [
        ("PK", "held_id", "bigint", False), ("FK", "subscription_id", "bigint", False),
        ("", "source_row_ref", "varchar", False), ("", "kind", "cancelled", False),
        ("", "rule_broken", "varchar", True), ("", "held_at", "timestamptz", False), ("", "resolution", "varchar null", False)],
        color=BAKSTEEN, dashed=True)
    b += cust + sub + chg + pay + dev + held

    # customer 1 -- 0..* subscription
    y = 150 + HEAD + 22 + 15
    b += f'<line x1="390" y1="{y}" x2="490" y2="{y}" stroke="{ESPRESSO}" stroke-width="2.2"/>'
    b += bar_one(390, y, ("x", -1)) + foot_many(490, y, ("x", 1))
    # subscription 1 -- 1..* status change
    y2 = y + ROW
    b += f'<line x1="850" y1="{y2}" x2="960" y2="{y2}" stroke="{ESPRESSO}" stroke-width="2.2"/>'
    b += bar_one(850, y2, ("x", -1)) + foot_one_many(960, y2, ("x", 1))
    # subscription 1 -- 0..* payment attempt, delivery, held
    sx, sy = 670, 150 + sh
    busy = 490
    b += f'<path d="M{sx} {sy}V{busy}H470M{sx} {busy}H1240M470 {busy}V560M810 {busy}V560M1240 {busy}V560" fill="none" stroke="{ESPRESSO}" stroke-width="2.2"/>'
    b += bar_one(sx, sy, ("y", -1))
    for x in (470, 810, 1240):
        b += foot_many(x, 560, ("y", 1))
    # the constraint
    b += f'<rect x="1370" y="150" width="190" height="{max(gh, 120)}" rx="12" fill="{ESPRESSO}"/>'
    b += t(1388, 184, "CHECK", 15, MONO, HONING, 700, spacing=1.5)
    b += wrap(1388, 214, ["kind <> 'cancelled'", "OR (initiator", "  IS NOT NULL", "  AND reason", "  IS NOT NULL)"], 13, MONO, CREMA, 22)
    b += wrap(1388, 350, ["Rows that fail it go", "to held_for_review", "instead."], 13, MONO, HONING, 21)

    # legend
    lx, ly = 60, 838
    b += t(lx, ly, "PK", 12, MONO, HONING, 700) + t(lx + 26, ly, "primary key", 12.5, MONO, MUTED)
    b += t(lx + 150, ly, "FK", 12, MONO, GRACHT, 700) + t(lx + 176, ly, "foreign key", 12.5, MONO, MUTED)
    b += t(lx + 300, ly, "red column", 12.5, MONO, BAKSTEEN, 600) + t(lx + 400, ly, "= carries a rule from the domain model", 12.5, MONO, MUTED)
    return frame(b, "Kelder domain model, ERD",
                 "CROW'S FOOT NOTATION · ONE SUBSCRIPTION, MANY EVENTS AROUND IT",
                 "Every consumer (agent, dashboards, board pack) reads these tables. Billing moving from Shopify to Recharge changes only the mapping into them.")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("domain_model_logical", logical), ("domain_model_erd", erd)):
        (OUT / f"{name}.svg").write_text(fn())
        print(f"wrote charts/out/{name}.svg")


if __name__ == "__main__":
    main()
