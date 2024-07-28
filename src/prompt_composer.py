import os
from dotenv import load_dotenv
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme
from openai import AsyncOpenAI
from datetime import datetime
from src.utils import get_chat_completion

# Load environment variables from .env file
load_dotenv()

# Use the API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class PromptComposer:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
        self.prompts = {
            'midjourney': self.load_prompt('prompts/midjourney.txt'),
            'udio': self.load_prompt('prompts/udio.txt')
        }
        self.console = Console(theme=Theme({"info": "cyan", "warning": "yellow", "error": "bold red", "success": "bold green"}))

    @staticmethod
    def load_prompt(file_path):
        with open(file_path, 'r') as file:
            return file.read()

    async def generate_completion(self, prompt_type, question):
        try:
            content = await get_chat_completion([
                {"role": "system", "content": self.prompts[prompt_type]},
                {"role": "user", "content": question}
            ])
            return content
        except Exception as e:
            self.console.print(f"[error]API error: {type(e).__name__} - {str(e)}[/error]")
            return None

    def save_output(self, prompt_type, question, output):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prompt_type}_{timestamp}.txt"
        with open(filename, "w") as f:
            f.write(f"Question: {question}\n\nOutput:\n{output}")
        return filename

    async def run(self):
        while True:
            self.console.print(Panel("=== Prompt Gen ===", style="bold blue"))
            self.console.print("[warning]Enter 'q' to quit.[/warning]")
            self.console.print("[info]Select prompt type:[/info]")
            self.console.print("1. Midjourney")
            self.console.print("2. Udio")

            prompt_type = await Prompt.ask("Choice (1/2/q)", choices=["1", "2", "q"], default="1")
            
            if prompt_type == 'q':
                self.console.print('[warning]Exiting... Goodbye![/warning]')
                break
            
            prompt_type = 'midjourney' if prompt_type == '1' else 'udio' if prompt_type == '2' else None
            if not prompt_type:
                self.console.print('[error]Invalid choice. Please try again.[/error]')
                continue

            question = await Prompt.ask(f"Describe the {'image' if prompt_type == 'midjourney' else 'music'} (or 'q' to quit)")
            
            if question.lower() == 'q':
                self.console.print('[warning]Exiting... Goodbye![/warning]')
                break
            
            if not question:
                self.console.print('[error]Please provide a description.[/error]')
                continue

            with self.console.status("[bold green]Generating...[/bold green]"):
                output = await self.generate_completion(prompt_type, question)
            if output:
                self.console.print(Panel(output, title="[info]Generated Output[/info]", expand=False))
                saved_file = self.save_output(prompt_type, question, output)
                self.console.print(f"[success]Saved to: {saved_file}[/success]")
            self.console.print("─" * 80)