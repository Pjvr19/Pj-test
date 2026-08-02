"""
CLI om de agent mee te testen.

Gebruik:
    python main.py

Typ 'stop', 'exit' of 'quit' om te stoppen.
"""
from colorama import Fore, Style, init as init_colorama

from agent import TradingAgent

# Zorgt dat kleurcodes ook werken in het klassieke Windows-opdrachtvenster
# (niet alleen in moderne terminals), en dat kleur na elke print() weer
# automatisch terug naar normaal gaat.
init_colorama(autoreset=True)


def main():
    print("Trading-assistent (read-only: geen echte trades, alleen marktdata + advies).")
    print("Typ 'stop' om te stoppen.\n")

    agent = TradingAgent()

    while True:
        # We printen "Jij: " apart (met kleur) i.p.v. als prompt-tekst aan
        # input() mee te geven - op Windows gaat kleur in een input()-prompt
        # namelijk niet altijd goed, via een losse print() wel betrouwbaar.
        print(f"{Fore.CYAN}Jij: {Style.RESET_ALL}", end="", flush=True)
        user_input = input().strip()

        if user_input.lower() in ("stop", "exit", "quit"):
            print("Tot ziens!")
            break

        if not user_input:
            continue

        antwoord = agent.send(user_input)
        print(f"\n{Fore.GREEN}Agent:{Style.RESET_ALL} {antwoord}\n")


if __name__ == "__main__":
    main()
