"""
Portfolio: houdt een virtuele (NEP-geld) portfolio bij in een lokaal
JSON-bestand (portfolio.json).

Dit is "paper trading": er wordt nooit echt geld of een echte exchange
gebruikt. Het is bedoeld om te testen of de suggesties van de agent
winstgevend zouden zijn, zonder enig financieel risico.
"""
import json
import os
from datetime import datetime, timezone

PORTFOLIO_FILE = "portfolio.json"
START_BALANCE_EUR = 1000.0


def _default_portfolio() -> dict:
    """Een nieuwe portfolio: startkapitaal in cash, nog geen holdings."""
    return {
        "cash_eur": START_BALANCE_EUR,
        "holdings": {},  # bv. {"bitcoin": 0.01234}
        "history": [],
    }


def load_portfolio() -> dict:
    """Leest de portfolio uit portfolio.json, of maakt een nieuwe aan als die nog niet bestaat."""
    if not os.path.exists(PORTFOLIO_FILE):
        return _default_portfolio()
    with open(PORTFOLIO_FILE, "r") as f:
        return json.load(f)


def save_portfolio(portfolio: dict) -> None:
    """Schrijft de portfolio terug naar portfolio.json."""
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)


def record_trade(
    portfolio: dict,
    trade_type: str,
    coin_id: str,
    quantity: float,
    price_eur: float,
    amount_eur: float,
) -> None:
    """Voegt een regel toe aan de (virtuele) transactiegeschiedenis."""
    portfolio["history"].append({
        "type": trade_type,
        "coin_id": coin_id,
        "quantity": quantity,
        "price_eur": price_eur,
        "amount_eur": amount_eur,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
