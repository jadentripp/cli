import os
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.theme import Theme
from cli.src.prompt_composer import PromptComposer
from cli.src.history import PromptHistory

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

HEADER = "AI Prompt Generator"

def run_cli_app():
    composer = PromptComposer()
    console.print(HEADER, style="bold cyan")
    composer.run()

def show_history(prompt_type, limit, view_index=None):
    history = PromptHistory()

    if view_index is not None:
        history.view_prompt(prompt_type, view_index)
    else:
        history.display_history(prompt_type, limit)

def main():
    parser = argparse.ArgumentParser(description="AI Prompt Generator CLI")
    parser.add_argument("--history", choices=["midjourney", "udio", "suno"], help="View history for a specific prompt type")
    parser.add_argument("--history-interactive", choices=["midjourney", "udio", "suno"], help="Interactive history browser")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of history items to display")
    parser.add_argument("--view", type=int, help="View a specific prompt by index")
    parser.add_argument("--search", help="Search term for filtering history")

    args = parser.parse_args()

    try:
        if args.history_interactive:
            history = PromptHistory()
            history.interactive_history(args.history_interactive)
        elif args.history:
            show_history(args.history, args.limit, args.view)
        else:
            run_cli_app()
    except KeyboardInterrupt:
        console.print("\n[info]Exiting.[/info]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()