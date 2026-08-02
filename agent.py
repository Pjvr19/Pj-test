"""
De agent-logica: praat met Claude via de Anthropic API, en voert tools uit
wanneer Claude daarom vraagt (tool use / function calling).

Kernidee van de "agent loop":
1. Stuur het gesprek (inclusief system prompt en tools) naar Claude.
2. Als Claude een tool wil gebruiken (stop_reason == "tool_use"), voeren
   wij die tool uit en sturen het resultaat terug naar Claude.
3. Dit herhaalt zich tot Claude geen tool meer nodig heeft en gewoon
   tekst teruggeeft - dan zijn we klaar en geven we dat antwoord terug.
"""
import anthropic

import config
from tools import TOOLS, TOOL_FUNCTIONS

# De system prompt bepaalt de "persoonlijkheid" en grenzen van de agent.
# Belangrijk: dit is PAPER TRADING - de agent koopt/verkoopt alleen met
# nepgeld in een lokaal bestand. Er is geen koppeling met een echte
# exchange en er wordt nooit echt geld gebruikt.
SYSTEM_PROMPT = (
    "Je bent een persoonlijke trading-assistent die oefent met paper "
    "trading. Je kunt actuele marktdata opzoeken, het internet doorzoeken "
    "voor actueel nieuws en context (bv. waarom een munt beweegt, of het "
    "algemene marktsentiment), en met NEP-geld uit een virtuele portfolio "
    "kopen en verkopen om te testen of een strategie winstgevend zou zijn. "
    "Er is GEEN koppeling met een echte exchange en er wordt nooit echt "
    "geld gebruikt - wees hier altijd expliciet over in je antwoorden. Leg "
    "kort uit waarom je een (virtuele) trade doet - gebruik gerust wat je "
    "via een zoekopdracht vond als onderbouwing - en vermeld dat dit geen "
    "financieel advies is en geen garantie voor toekomstige resultaten."
)


class TradingAgent:
    """Simpele agent die met Claude praat en tools kan aanroepen."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        # De conversatiegeschiedenis houden we hier bij, zodat de agent
        # eerdere berichten in het gesprek "onthoudt".
        self.messages = []

    def _run_tool(self, name: str, tool_input: dict) -> str:
        """Zoekt de juiste tool-functie op basis van de naam en voert 'm uit."""
        tool_function = TOOL_FUNCTIONS.get(name)
        if tool_function is None:
            return f"Onbekende tool: {name}"
        return tool_function(**tool_input)

    def send(self, user_message: str) -> str:
        """
        Stuurt een bericht van de gebruiker naar Claude, handelt eventuele
        tool-aanroepen af, en geeft het uiteindelijke tekstantwoord terug.
        """
        self.messages.append({"role": "user", "content": user_message})

        # Deze loop blijft draaien zolang Claude tools wil gebruiken.
        while True:
            response = self.client.messages.create(
                model=config.MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.messages,
            )

            # Bewaar Claude's antwoord (incl. eventuele tool_use blokken)
            # in de geschiedenis - anders "vergeet" Claude wat het net deed.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                # Claude is klaar met tools; pak de tekst uit het antwoord.
                text_blocks = [block.text for block in response.content if block.type == "text"]
                return "\n".join(text_blocks)

            # Claude wil een of meerdere tools gebruiken. Voer ze allemaal
            # uit en stuur alle resultaten in één keer terug.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            self.messages.append({"role": "user", "content": tool_results})
