"""
CLI om de agent mee te testen.

Gebruik:
    python main.py

Typ 'stop', 'exit' of 'quit' om te stoppen.
"""
from agent import TradingAgent


def main():
    print("Trading-assistent (read-only: geen echte trades, alleen marktdata + advies).")
    print("Typ 'stop' om te stoppen.\n")

    agent = TradingAgent()

    while True:
        user_input = input("Jij: ").strip()

        if user_input.lower() in ("stop", "exit", "quit"):
            print("Tot ziens!")
            break

        if not user_input:
            continue

        antwoord = agent.send(user_input)
        print(f"\nAgent: {antwoord}\n")


if __name__ == "__main__":
    main()
