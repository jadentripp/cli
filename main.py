import asyncio
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme
from rich.table import Table
from rich.text import Text
from src.youtube_summarizer import process_video
from src.prompt_composer import PromptComposer
from src.utils import get_video_id
import logging

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
╭──────────────────────────────────────────────────────╮
│                                                      │
│   YouTube Summarizer and Prompt Generator            │
│                                                      │
╰─────────────────────────────────────────────────────╯
"""

logger = logging.getLogger(__name__)

async def run_cli_app():
    composer = PromptComposer()

    console.print(Panel(Text(HEADER, style="bold cyan"), expand=False))
    console.print("[green]API key loaded successfully![/green]")

    while True:
        table = Table(show_header=False, expand=False, box=None)
        table.add_row("[cyan]1.[/cyan]", "Summarize YouTube Video", "[dim]Generate a summary of a YouTube video[/dim]")
        table.add_row("[cyan]2.[/cyan]", "Generate Prompts", "[dim]Create prompts for Midjourney or Udio[/dim]")
        table.add_row("[cyan]q.[/cyan]", "Quit", "[dim]Exit the application[/dim]")
        
        console.print(table)

        choice = Prompt.ask("\nChoose an option or enter a YouTube URL", default="1")

        if choice.lower() == 'q':
            console.print("[warning]Thank you for using the application. Goodbye![/warning]")
            break

        if get_video_id(choice):
            # If the input is a valid YouTube URL, process it
            try:
                with console.status("[bold green]Processing video...[/bold green]") as status:
                    await process_video(choice)
            except Exception as e:
                logger.exception(f"An error occurred while processing the video: {str(e)}")
                console.print(f"[error]An error occurred while processing the video: {str(e)}[/error]")
        elif choice == "1":
            url = Prompt.ask("\nPlease enter a YouTube video URL")
            try:
                with console.status("[bold green]Processing video...[/bold green]") as status:
                    await process_video(url)
            except Exception as e:
                logger.exception(f"An error occurred while processing the video: {str(e)}")
                console.print(f"[error]An error occurred while processing the video: {str(e)}[/error]")
        elif choice == "2":
            await composer.run()
        else:
            console.print("[error]Invalid option. Please try again.[/error]")

        console.print("\n" + "─" * 50 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_cli_app())
    except Exception as e:
        console.print(f"[bold red]An error occurred: {str(e)}[/bold red]")