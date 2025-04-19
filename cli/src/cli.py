import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from cli.src.prompt_composer import PromptComposer

# Load environment variables from .env file
load_dotenv()

# Check for OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please check your .env file.")

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
})

console = Console(theme=custom_theme)

HEADER = """
AI Prompt Generator (with OpenAI Agents SDK)
"""

def main():
    try:
        composer = PromptComposer()
        console.print(Panel(HEADER, style="bold cyan", expand=False))
        console.print("[green]API key loaded successfully![/green]")
        composer.run()
    except KeyboardInterrupt:
        console.print("\n[info]Exiting.[/info]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()