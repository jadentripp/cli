import os
from dotenv import load_dotenv
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme
from openai import AsyncOpenAI
from datetime import datetime
from src.utils import get_chat_completion, count_tokens, calculate_prompt_price

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
            # Calculate input tokens
            system_prompt = self.prompts[prompt_type]
            input_tokens = count_tokens(system_prompt + question)
            
            content = await get_chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ])
            
            # Calculate output tokens and price
            output_tokens = count_tokens(content)
            price_info = calculate_prompt_price(input_tokens, output_tokens)
            
            # Display pricing information
            self.console.print("\n[bold cyan]Cost Information:[/bold cyan]")
            self.console.print(f"Input Tokens: {price_info['input_tokens']}")
            self.console.print(f"Output Tokens: {price_info['output_tokens']}")
            self.console.print(f"Total Cost: ${price_info['total_cost']:.4f}")
            
            return content
        except Exception as e:
            self.console.print(f"[error]API error: {type(e).__name__} - {str(e)}[/error]")
            return None

    def save_output(self, prompt_type, question, output):
        # Create output directory if it doesn't exist
        output_dir = os.path.join('output', prompt_type)
        os.makedirs(output_dir, exist_ok=True)

        # Create a filename based on the input prompt
        safe_filename = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in question]).rstrip()
        safe_filename = safe_filename[:50]  # Limit filename length
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_filename}_{timestamp}.txt"
        
        file_path = os.path.join(output_dir, filename)
        with open(file_path, "w", encoding='utf-8') as f:
            f.write(f"Prompt: {question}\n\nOutput:\n{output}")
        return file_path

    async def run(self):
        while True:
            self.console.print("\n=== Prompt Gen ===", style="bold blue")
            self.console.print("[warning]Enter 'q' to quit.[/warning]")
            self.console.print("[info]Select prompt type:[/info]")
            self.console.print("1. Midjourney")
            self.console.print("2. Udio")

            prompt_type = Prompt.ask("Choice (1/2/q)", choices=["1", "2", "q"], default="1")
            
            if prompt_type == 'q':
                self.console.print('[warning]Exiting... Goodbye![/warning]')
                break
            
            prompt_type = 'midjourney' if prompt_type == '1' else 'udio' if prompt_type == '2' else None
            if not prompt_type:
                self.console.print('[error]Invalid choice. Please try again.[/error]')
                continue

            question = Prompt.ask(f"Describe the {'image' if prompt_type == 'midjourney' else 'music'} (or 'q' to quit)")
            
            if question.lower() == 'q':
                self.console.print('[warning]Exiting... Goodbye![/warning]')
                break
            
            if not question:
                self.console.print('[error]Please provide a description.[/error]')
                continue

            with self.console.status("[bold green]Generating...[/bold green]"):
                output = await self.generate_completion(prompt_type, question)
            if output:
                # Print the output without panel borders
                self.console.print("\nGenerated Output:", style="bold cyan")
                self.console.print(output)
                saved_file = self.save_output(prompt_type, question, output)
                self.console.print(f"\n[success]Saved to: {saved_file}[/success]")
            self.console.print()  # Just add a newline for spacing