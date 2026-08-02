"""
Tools die de agent kan aanroepen.

Hoe werkt tool use bij Claude?
1. Wij geven Claude een lijst met "schema's": naam, beschrijving en
   verwachte input van elke tool (zie GET_CRYPTO_PRICE_SCHEMA).
2. Als Claude denkt dat een tool nodig is om de vraag te beantwoorden,
   stuurt het GEEN echte code-aanroep - het stuurt terug: "ik wil tool X
   gebruiken met deze input".
3. Onze eigen code (in agent.py) voert de bijbehorende Python-functie dan
   pas echt uit, en stuurt het resultaat terug naar Claude.

Er zijn twee soorten tools hier:
- get_crypto_price: haalt alleen marktdata op (read-only).
- buy_crypto / sell_crypto / get_portfolio_status: "paper trading" - de
  agent koopt/verkoopt met NEP-geld uit een lokaal bestand (portfolio.json).
  Er wordt NOOIT een echte order op een echte exchange geplaatst.
"""
import requests

from portfolio import (
    START_BALANCE_EUR,
    load_portfolio,
    record_trade,
    save_portfolio,
)

# Schema dat we aan Claude geven zodat het weet dat deze tool bestaat,
# waarvoor hij dient, en welke input hij verwacht.
GET_CRYPTO_PRICE_SCHEMA = {
    "name": "get_crypto_price",
    "description": (
        "Haalt de actuele prijs en de verandering over de laatste 24 uur "
        "op van een cryptomunt, via de gratis CoinGecko API. Gebruik dit "
        "voor vragen over actuele koersen, bijvoorbeeld van bitcoin of "
        "ethereum. Deze tool voert GEEN trades uit, hij haalt alleen data op."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "coin_id": {
                "type": "string",
                "description": (
                    "CoinGecko coin-id in kleine letters, bv. 'bitcoin', "
                    "'ethereum' of 'solana'."
                ),
            },
            "vs_currency": {
                "type": "string",
                "description": "Valuta om de prijs in uit te drukken, bv. 'eur' of 'usd'.",
            },
        },
        "required": ["coin_id"],
    },
}


def get_crypto_price(coin_id: str, vs_currency: str = "eur") -> str:
    """
    Haalt live prijsdata op via de publieke CoinGecko API (geen API-key
    nodig). Geeft een leesbare tekst terug - dat is wat Claude als
    tool-resultaat te zien krijgt.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": vs_currency,
        "include_24hr_change": "true",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return f"Fout bij ophalen van marktdata: {e}"

    if coin_id not in data or vs_currency not in data[coin_id]:
        return f"Geen data gevonden voor coin_id '{coin_id}' in '{vs_currency}'. Klopt de naam?"

    price = data[coin_id][vs_currency]
    change = data[coin_id].get(f"{vs_currency}_24h_change")
    change_text = f"{change:+.2f}%" if change is not None else "onbekend"

    return f"{coin_id} staat op {price} {vs_currency.upper()} ({change_text} laatste 24 uur)."


def _fetch_price_eur(coin_id: str) -> float | None:
    """
    Interne helper die alleen het kale prijsgetal in euro teruggeeft
    (geen opgemaakte tekst). Wordt gebruikt door buy_crypto/sell_crypto/
    get_portfolio_status om de virtuele waarde te berekenen.
    Geeft None terug als de prijs niet opgehaald kon worden.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": "eur"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None

    return data.get(coin_id, {}).get("eur")


BUY_CRYPTO_SCHEMA = {
    "name": "buy_crypto",
    "description": (
        "Koopt een cryptomunt met NEP-geld uit de virtuele portfolio "
        "(paper trading). Er wordt GEEN echt geld en GEEN echte exchange "
        "gebruikt - dit is puur een simulatie om te testen of een keuze "
        "winstgevend zou zijn."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "coin_id": {
                "type": "string",
                "description": "CoinGecko coin-id, bv. 'bitcoin' of 'ethereum'.",
            },
            "amount_eur": {
                "type": "number",
                "description": "Hoeveel virtueel geld (in euro) je wil investeren.",
            },
        },
        "required": ["coin_id", "amount_eur"],
    },
}


def buy_crypto(coin_id: str, amount_eur: float) -> str:
    """Koopt (virtueel) een cryptomunt tegen de actuele prijs."""
    if amount_eur <= 0:
        return "Ongeldig bedrag: amount_eur moet groter dan 0 zijn."

    portfolio = load_portfolio()

    if amount_eur > portfolio["cash_eur"]:
        return (
            f"Niet genoeg virtueel geld: je hebt {portfolio['cash_eur']:.2f} EUR, "
            f"maar wil {amount_eur:.2f} EUR investeren."
        )

    price = _fetch_price_eur(coin_id)
    if price is None:
        return f"Kon geen actuele prijs ophalen voor '{coin_id}' - aankoop geannuleerd."

    quantity = amount_eur / price
    portfolio["cash_eur"] -= amount_eur
    portfolio["holdings"][coin_id] = portfolio["holdings"].get(coin_id, 0.0) + quantity
    record_trade(portfolio, "buy", coin_id, quantity, price, amount_eur)
    save_portfolio(portfolio)

    return (
        f"[PAPER TRADE - nepgeld] Gekocht: {quantity:.6f} {coin_id} voor "
        f"{amount_eur:.2f} EUR (koers: {price:.2f} EUR). "
        f"Resterend virtueel saldo: {portfolio['cash_eur']:.2f} EUR."
    )


SELL_CRYPTO_SCHEMA = {
    "name": "sell_crypto",
    "description": (
        "Verkoopt een cryptomunt uit de virtuele portfolio (paper trading) "
        "voor NEP-geld. Er wordt GEEN echte exchange gebruikt. Als het "
        "gevraagde bedrag hoger is dan wat je bezit, wordt gewoon alles "
        "verkocht wat je hebt."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "coin_id": {
                "type": "string",
                "description": "CoinGecko coin-id van de munt die je wil verkopen.",
            },
            "amount_eur": {
                "type": "number",
                "description": "Hoeveel virtueel geld (in euro) je wil vrijmaken door te verkopen.",
            },
        },
        "required": ["coin_id", "amount_eur"],
    },
}


def sell_crypto(coin_id: str, amount_eur: float) -> str:
    """Verkoopt (virtueel) een deel van een holding tegen de actuele prijs."""
    if amount_eur <= 0:
        return "Ongeldig bedrag: amount_eur moet groter dan 0 zijn."

    portfolio = load_portfolio()
    held_quantity = portfolio["holdings"].get(coin_id, 0.0)

    if held_quantity <= 0:
        return f"Je hebt geen '{coin_id}' in je virtuele portfolio om te verkopen."

    price = _fetch_price_eur(coin_id)
    if price is None:
        return f"Kon geen actuele prijs ophalen voor '{coin_id}' - verkoop geannuleerd."

    held_value_eur = held_quantity * price
    # Kun je niet meer verkopen dan je daadwerkelijk bezit.
    amount_eur = min(amount_eur, held_value_eur)
    quantity = amount_eur / price

    portfolio["holdings"][coin_id] = held_quantity - quantity
    portfolio["cash_eur"] += amount_eur
    record_trade(portfolio, "sell", coin_id, quantity, price, amount_eur)
    save_portfolio(portfolio)

    return (
        f"[PAPER TRADE - nepgeld] Verkocht: {quantity:.6f} {coin_id} voor "
        f"{amount_eur:.2f} EUR (koers: {price:.2f} EUR). "
        f"Nieuw virtueel saldo: {portfolio['cash_eur']:.2f} EUR."
    )


GET_PORTFOLIO_STATUS_SCHEMA = {
    "name": "get_portfolio_status",
    "description": (
        "Geeft een overzicht van de virtuele (paper trading) portfolio: "
        "hoeveel nepgeld er nog is, welke munten er 'in bezit' zijn met "
        "hun actuele waarde, en de totale winst/verlies sinds de start."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


def get_portfolio_status() -> str:
    """Geeft een leesbaar overzicht van de virtuele portfolio en de winst/verlies."""
    portfolio = load_portfolio()
    lines = [f"Virtueel cash: {portfolio['cash_eur']:.2f} EUR"]

    total_value = portfolio["cash_eur"]
    for coin_id, quantity in portfolio["holdings"].items():
        if quantity <= 0:
            continue
        price = _fetch_price_eur(coin_id)
        if price is None:
            lines.append(f"- {coin_id}: {quantity:.6f} (actuele prijs niet beschikbaar)")
            continue
        value = quantity * price
        total_value += value
        lines.append(f"- {coin_id}: {quantity:.6f} = {value:.2f} EUR")

    profit = total_value - START_BALANCE_EUR
    lines.append(f"Totale portfoliowaarde: {total_value:.2f} EUR")
    lines.append(f"Winst/verlies sinds start ({START_BALANCE_EUR:.2f} EUR): {profit:+.2f} EUR")

    return "\n".join(lines)


# Alle tool-schema's die we aan Claude doorgeven.
TOOLS = [
    GET_CRYPTO_PRICE_SCHEMA,
    BUY_CRYPTO_SCHEMA,
    SELL_CRYPTO_SCHEMA,
    GET_PORTFOLIO_STATUS_SCHEMA,
]

# Koppelt de naam van een tool (zoals Claude die noemt) aan de Python-
# functie die 'm daadwerkelijk uitvoert.
TOOL_FUNCTIONS = {
    "get_crypto_price": get_crypto_price,
    "buy_crypto": buy_crypto,
    "sell_crypto": sell_crypto,
    "get_portfolio_status": get_portfolio_status,
}
