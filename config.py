"""
Config: laadt instellingen (zoals de Anthropic API-key) uit het .env bestand.

Waarom een apart config-bestand?
- Zo staat je geheime API-key nergens hardcoded in de code.
- Andere bestanden (agent.py) importeren gewoon `config` en hoeven zich
  niet druk te maken over .env-bestanden.
"""
import os

from dotenv import load_dotenv

# Leest het .env bestand in en zet de waarden erin als omgevingsvariabelen.
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Welk Claude-model de agent gebruikt. Standaard claude-opus-5, maar via
# .env kun je dit overschrijven (bv. naar een goedkoper model).
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

if not ANTHROPIC_API_KEY:
    raise ValueError(
        "ANTHROPIC_API_KEY ontbreekt. Maak een .env bestand aan "
        "(kopieer .env.example) en vul je eigen API-key in."
    )
