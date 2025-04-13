import os
import re
from dotenv import load_dotenv
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from openai import AsyncOpenAI
from datetime import datetime
import questionary
from questionary import Style as QuestionaryStyle
from src.utils import count_tokens, calculate_prompt_price, get_agent_completion
from src.agents_config import create_midjourney_agent, create_udio_agent

# Load environment variables from .env file
load_dotenv()

# Use the API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class PromptComposer:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.models = {
            'gpt-4o-mini': {
                'name': 'GPT-4o mini',
                'description': 'Faster and more cost-effective'
            },
            'gpt-4o-2024-11-20': {
                'name': 'GPT-4o (Nov 2024)',
                'description': 'Powerful and accurate snapshot model'
            }
        }
        self.current_model = "gpt-4o-mini"  # Default model
        self.prompts = {
            'midjourney': self.load_prompt('prompts/midjourney.txt'),
            'udio': self.load_prompt('prompts/udio.txt')
        }
        # Initialize agents
        self.update_agents()
        # Initialize history for each prompt type
        self.history = {
            'midjourney': [],
            'udio': []
        }
        self.console = Console(theme=Theme({"info": "cyan", "warning": "yellow", "error": "bold red", "success": "bold green"}))

    def update_agents(self):
        """Update agents with the current model."""
        self.agents = {
            'midjourney': create_midjourney_agent(model=self.current_model),
            'udio': create_udio_agent(model=self.current_model)
        }

    @staticmethod
    def load_prompt(file_path):
        with open(file_path, 'r') as file:
            return file.read()

    async def generate_completion(self, prompt_type, question):
        try:
            # Calculate input tokens
            system_prompt = self.prompts[prompt_type]
            input_tokens = count_tokens(system_prompt + question)

            # Use the Agents SDK instead of direct API calls
            agent = self.agents[prompt_type]
            content = await get_agent_completion(agent, question)

            # Calculate output tokens and price
            output_tokens = count_tokens(content)
            price_info = calculate_prompt_price(input_tokens, output_tokens, self.current_model)

            # Display pricing information
            self.console.print("\n[bold cyan]Cost Information:[/bold cyan]")
            self.console.print(f"Model: {self.models[self.current_model]['name']}")
            self.console.print(f"Input Tokens: {price_info['input_tokens']}")
            self.console.print(f"Output Tokens: {price_info['output_tokens']}")
            self.console.print(f"Total Cost: ${price_info['total_cost']:.4f}")

            return content
        except Exception as e:
            self.console.print(f"[error]API error: {type(e).__name__} - {str(e)}[/error]")
            return None

    def view_history(self, prompt_type):
        """View history for a specific prompt type."""
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.join('output', prompt_type)
            if not os.path.exists(output_dir):
                self.console.print(f"[warning]No history found for {prompt_type}[/warning]")
                return

            # Get all files in the directory
            files = os.listdir(output_dir)
            files = [f for f in files if f.endswith('.txt')]

            if not files:
                self.console.print(f"[warning]No history found for {prompt_type}[/warning]")
                return

            # Sort files by creation time (newest first)
            files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)), reverse=True)

            # Display the files in a table
            from rich.table import Table
            table = Table(title=f"Recent {prompt_type.capitalize()} Prompts")
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Date", style="cyan")
            table.add_column("Prompt", style="green")

            # Add rows to the table
            for i, file in enumerate(files[:10]):
                file_path = os.path.join(output_dir, file)
                date_str = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M")

                # Read the prompt from the file
                prompt = ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        prompt_match = re.search(r'Prompt: (.*?)\n\nOutput:', content, re.DOTALL)
                        if prompt_match:
                            prompt = prompt_match.group(1).strip()
                except Exception:
                    prompt = "Error reading file"

                # Truncate long prompts
                if len(prompt) > 60:
                    prompt = prompt[:57] + "..."

                table.add_row(str(i + 1), date_str, prompt)

            # Display the table
            self.console.print(table)

            # Create choices for questionary
            prompt_choices = []
            for i, file in enumerate(files[:10]):
                file_path = os.path.join(output_dir, file)
                date_str = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M")

                # Read the prompt from the file
                prompt_display = ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        prompt_match = re.search(r'Prompt: (.*?)\n\nOutput:', content, re.DOTALL)
                        if prompt_match:
                            prompt_display = prompt_match.group(1).strip()
                except Exception:
                    prompt_display = "Error reading file"

                # Truncate long prompts
                if len(prompt_display) > 60:
                    prompt_display = prompt_display[:57] + "..."

                prompt_choices.append(f"{i+1}. {date_str} - {prompt_display}")

            # Add a back option
            prompt_choices.append("Back to main menu")

            # Ask if user wants to view a specific prompt using questionary
            custom_style = QuestionaryStyle([
                ("question", "bold cyan"),
                ("answer", "bold green"),
                ("pointer", "bold cyan"),
                ("highlighted", "bold cyan"),
                ("selected", "bold green"),
            ])

            selection = questionary.select(
                "Select a prompt to view details:",
                choices=prompt_choices,
                style=custom_style
            ).ask()

            # Handle selection
            if selection == "Back to main menu":
                return

            # Extract index from selection
            idx = int(selection.split(".")[0]) - 1
            file_path = os.path.join(output_dir, files[idx])

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    parts = content.split("\n\nOutput:\n", 1)
                    if len(parts) == 2:
                        prompt = parts[0].replace("Prompt: ", "").strip()
                        output = parts[1].strip()

                        # Display the prompt and output
                        from rich.panel import Panel
                        self.console.print(Panel(f"[bold cyan]Prompt:[/bold cyan]\n{prompt}", expand=False))
                        self.console.print(Panel(f"[bold green]Output:[/bold green]\n{output}", expand=False))

                        # Ask user to press Enter to continue
                        questionary.press_any_key_to_continue("Press any key to go back...").ask()
                    else:
                        self.console.print(Panel(content, title="Content", expand=False))
                        questionary.press_any_key_to_continue("Press any key to go back...").ask()
            except Exception as e:
                self.console.print(f"[error]Error reading file: {str(e)}[/error]")
                questionary.press_any_key_to_continue("Press any key to go back...").ask()
        except Exception as e:
            self.console.print(f"[error]Error viewing history: {str(e)}[/error]")

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

    def run(self):
        while True:
            self.console.print("\n=== Prompt Generator ===", style="bold blue")
            self.console.print("[info]Use arrow keys to navigate and Enter to select:[/info]")

            # Define custom style for questionary
            custom_style = QuestionaryStyle([
                ("question", "bold cyan"),
                ("answer", "bold green"),
                ("pointer", "bold cyan"),
                ("highlighted", "bold cyan"),
                ("selected", "bold green"),
            ])

            # Use questionary for arrow key navigation
            choices = [
                "Generate Midjourney prompts for image creation",
                "Generate Udio prompts for music creation",
                "View history of previously generated prompts",
                f"Switch model (Current: {self.models[self.current_model]['name']})",
                "Quit the application"
            ]

            # Display the menu with arrow key navigation
            selection = questionary.select(
                "Select an option:",
                choices=choices,
                style=custom_style
            ).ask()

            # Map selection to prompt type
            if selection == choices[0]:  # Midjourney
                prompt_type = "1"
            elif selection == choices[1]:  # Udio
                prompt_type = "2"
            elif selection == choices[2]:  # History
                prompt_type = "h"
            elif selection == choices[3]:  # Switch model
                prompt_type = "m"
            elif selection == choices[4]:  # Quit
                prompt_type = "q"
            else:
                prompt_type = "1"  # Default to Midjourney

            if prompt_type == 'q':
                self.console.print('[warning]Exiting... Goodbye![/warning]')
                break

            if prompt_type == 'h':
                # Use questionary for history type selection
                history_selection = questionary.select(
                    "Select history type:",
                    choices=[
                        "Midjourney prompts history",
                        "Udio prompts history"
                    ],
                    style=custom_style
                ).ask()

                # Map selection to history type
                history_type = 'midjourney' if history_selection == "Midjourney prompts history" else 'udio'

                # Show history
                self.view_history(history_type)
                continue

            if prompt_type == 'm':
                # Use questionary to select a new model
                model_choices = [
                    f"{key}: {value['name']} - {value['description']}" for key, value in self.models.items()
                ]

                selected_model = questionary.select(
                    "Select a model:",
                    choices=model_choices,
                    style=custom_style
                ).ask()

                if selected_model:
                    # Extract the model key from the selection
                    new_model_key = selected_model.split(':')[0]
                    if new_model_key in self.models:
                        self.current_model = new_model_key
                        self.update_agents()
                        self.console.print(f"[success]Switched to model: {self.models[self.current_model]['name']}[/success]")
                    else:
                        self.console.print("[error]Invalid model selection.[/error]")
                continue

            prompt_type = 'midjourney' if prompt_type == '1' else 'udio' if prompt_type == '2' else None
            if not prompt_type:
                self.console.print('[error]Invalid choice. Please try again.[/error]')
                continue

            # Use questionary for prompt input
            question = questionary.text(
                f"Describe the {'image' if prompt_type == 'midjourney' else 'music'} (or 'q' to quit):",
                style=custom_style
            ).ask()

            if not question:
                self.console.print('[error]Please provide a description.[/error]')
                continue

            if question.lower() == 'q':
                self.console.print('[warning]Exiting... Goodbye![/warning]')
                break

            with self.console.status("[bold green]Generating...[/bold green]"):
                # Run the async function in a new event loop
                output = asyncio.run(self.generate_completion(prompt_type, question))
            if output:
                # Print the output without panel borders
                self.console.print("\nGenerated Output:", style="bold cyan")
                self.console.print(output)
                saved_file = self.save_output(prompt_type, question, output)
                self.console.print(f"\n[success]Saved to: {saved_file}[/success]")
            self.console.print()  # Just add a newline for spacing