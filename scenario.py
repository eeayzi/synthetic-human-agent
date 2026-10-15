"""Validate local fixture data before opening any desktop application."""
from decimal import Decimal
import html
import json
import re


def load_scenario(path):
    with open(path, encoding="utf-8-sig") as file:
        data = json.load(file)
    if not isinstance(data, dict) or set(data) != {"title", "currency", "items"}:
        raise ValueError("Scenario requires title, currency, items")
    def label(value, name):
        if (not isinstance(value, str) or not value.strip() or len(value) > 120
                or any(ord(c) < 32 for c in value) or value[0] in "=+-@"):
            raise ValueError(f"Invalid {name}")
        return value
    label(data["title"], "title")
    if not isinstance(data["currency"], str) or not re.fullmatch(r"[A-Z]{3}", data["currency"]):
        raise ValueError("currency must be a three-letter uppercase code")
    if not isinstance(data["items"], list) or not 1 <= len(data["items"]) <= 100:
        raise ValueError("items must contain 1–100 rows")
    total = Decimal("0.00")
    for item in data["items"]:
        if not isinstance(item, dict) or set(item) != {"name", "quantity", "unit_price"}:
            raise ValueError("Each item requires name, quantity, unit_price")
        label(item["name"], "item name")
        q = item["quantity"]
        if isinstance(q, bool) or not isinstance(q, int) or not 1 <= q <= 10000:
            raise ValueError("quantity must be an integer from 1 to 10000")
        raw = item["unit_price"]
        if not isinstance(raw, str) or not re.fullmatch(r"\d{1,7}(?:\.\d{1,2})?", raw):
            raise ValueError("unit_price must be a nonnegative decimal string with up to two decimals")
        price = Decimal(raw)
        item["unit_price"] = format(price, ".2f")
        item["line_total"] = format(q * price, ".2f")
        total += q * price
    data["total"] = format(total, ".2f")
    return data


def brief_html(data):
    rows = "".join(f"<tr><td>{html.escape(i['name'])}</td><td>{i['quantity']}</td>"
                   f"<td>{i['unit_price']}</td></tr>" for i in data["items"])
    return ("<!doctype html><meta charset='utf-8'><title>Synthetic project brief</title>"
            "<style>body{font:20px system-ui;max-width:850px;margin:70px auto}"
            "td,th{padding:16px;text-align:left}section{margin-top:500px}</style>"
            f"<h1>{html.escape(data['title'])}</h1><p>Controlled synthetic training fixture.</p>"
            "<table><tr><th>Item</th><th>Quantity</th><th>Unit price</th></tr>" + rows +
            "</table><a href='#instructions'>Read instructions</a><section id='instructions'>"
            "<h2>Instructions</h2><p>Calculate the budget in Excel, then write and verify a Word summary.</p>"
            "</section>")


def report_text(data, run_id):
    return (f"{data['title']}\nSynthetic training report\nRun ID: {run_id}\n\n"
            + "\n".join(f"{i['name']}: {i['quantity']} x {i['unit_price']} = {i['line_total']}"
                         for i in data["items"])
            + f"\n\nVerified budget total: {data['currency']} {data['total']}\n")
