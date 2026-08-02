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

Deze tool is bewust read-only: hij haalt alleen marktdata op en voert
nooit zelf een order/trade uit.
"""
import requests

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


# Alle tool-schema's die we aan Claude doorgeven.
TOOLS = [GET_CRYPTO_PRICE_SCHEMA]

# Koppelt de naam van een tool (zoals Claude die noemt) aan de Python-
# functie die 'm daadwerkelijk uitvoert.
TOOL_FUNCTIONS = {
    "get_crypto_price": get_crypto_price,
}
