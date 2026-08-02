"""
Journal: een simpel handelsdagboek waarin de agent kort bijhoudt waarom
hij bepaalde (virtuele) trades deed of wat hij leerde uit nieuws.

Dit bestand wordt bij het opstarten van een nieuw gesprek weer ingelezen
(zie agent.py), zodat de agent kan "voortbouwen" op eerdere sessies. Dit
is GEEN echt geheugen van het model zelf (het model leert niet bij) - het
is gewoon een tekstbestand dat we er zelf bij plakken in de system prompt.
"""
import json
import os
from datetime import datetime, timezone

JOURNAL_FILE = "journal.json"

# Hoeveel van de meest recente aantekeningen we aan de agent laten zien
# bij de start van een nieuw gesprek, zodat de system prompt niet
# onbeperkt blijft groeien naarmate je de agent vaker gebruikt.
MAX_NOTES_SHOWN = 10


def load_notes() -> list:
    """Leest alle aantekeningen uit journal.json (lege lijst als het bestand nog niet bestaat)."""
    if not os.path.exists(JOURNAL_FILE):
        return []
    with open(JOURNAL_FILE, "r") as f:
        return json.load(f)


def add_note(note: str) -> None:
    """Voegt een nieuwe aantekening toe en slaat het bestand op."""
    notes = load_notes()
    notes.append({
        "note": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    with open(JOURNAL_FILE, "w") as f:
        json.dump(notes, f, indent=2)


def recent_notes_summary() -> str:
    """
    Geeft een leesbare samenvatting van de meest recente aantekeningen,
    bedoeld om aan het begin van een gesprek aan de system prompt toe te
    voegen. Geeft een lege string terug als er nog geen aantekeningen zijn.
    """
    notes = load_notes()
    if not notes:
        return ""

    recent = notes[-MAX_NOTES_SHOWN:]
    lines = ["Eerdere aantekeningen uit je handelsdagboek (nieuwste onderaan):"]
    for entry in recent:
        lines.append(f"- [{entry['timestamp']}] {entry['note']}")
    return "\n".join(lines)
