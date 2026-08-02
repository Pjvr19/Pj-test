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
        # Sommige tools (zoals web_search met dynamische filtering) draaien
        # intern soms een klein stukje code uit in een tijdelijke sandbox
        # ("container"). Als zo'n actie nog niet volledig is afgerond, moet
        # je bij het vólgende verzoek diezelfde container weer meesturen,
        # anders geeft de API een foutmelding. We onthouden 'm hier zodra
        # we er een terugkrijgen.
        self.container_id = None

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
            # We bouwen de argumenten op in een dict, zodat we "container"
            # alleen meesturen als we er al één hebben (de eerste keer in
            # een gesprek meestal nog niet).
            request_kwargs = {
                "model": config.MODEL,
                # Claude Opus 5 denkt standaard eerst intern na, en dat
                # verbruikt ruimte uit hetzelfde budget als het uiteindelijke
                # antwoord. Bij complexe vragen (meerdere munten analyseren
                # en verhandelen) is 1024 te weinig - dan raakt het budget op
                # tijdens het nadenken en blijft er niks over voor de tekst.
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "tools": TOOLS,
                "messages": self.messages,
            }
            if self.container_id:
                request_kwargs["container"] = self.container_id

            response = self.client.messages.create(**request_kwargs)

            # Onthoud het container-ID als deze response er één gebruikt
            # heeft, zodat we 'm bij het volgende verzoek weer meesturen.
            if getattr(response, "container", None):
                self.container_id = response.container.id

            # Bewaar Claude's antwoord (incl. eventuele tool_use blokken)
            # in de geschiedenis - anders "vergeet" Claude wat het net deed.
            self.messages.append({"role": "assistant", "content": response.content})

            # Laat live zien waar Claude mee bezig is. Zonder dit blijft het
            # scherm helemaal stil totdat ALLES klaar is - bij een vraag die
            # meerdere zoekopdrachten en/of trades achter elkaar kost, kan
            # dat minutenlang aanvoelen alsof er niks gebeurt.
            for block in response.content:
                if block.type == "server_tool_use" and block.name == "web_search":
                    query = block.input.get("query", "")
                    print(f"  [ZOEKT OP INTERNET] {query}")
                elif block.type == "tool_use":
                    print(f"  [TOOL] {block.name}({block.input})")

            if response.stop_reason != "tool_use":
                # Claude is klaar met tools; pak de tekst uit het antwoord.
                text_blocks = [block.text for block in response.content if block.type == "text"]
                antwoord = "\n".join(text_blocks)

                # Vangnet: als er toch geen tekst overblijft (bv. omdat het
                # budget alsnog op is voor een hele grote vraag), geef een
                # duidelijke melding in plaats van stilzwijgend niets terug
                # te geven.
                if not antwoord:
                    return (
                        "(Geen tekstantwoord ontvangen - de vraag was waarschijnlijk "
                        "te complex voor de beschikbare ruimte. Probeer een kortere "
                        "of specifiekere vraag, of stel 'm in kleinere stapjes.)"
                    )
                return antwoord

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
