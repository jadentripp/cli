import os
import sys
import re
from dotenv import load_dotenv
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from openai import AsyncOpenAI
from datetime import datetime
import questionary
from questionary import Style as QuestionaryStyle, Choice
import json
from cli.src.utils import count_tokens, calculate_prompt_price, get_agent_completion, copy_to_clipboard
from cli.src.agents_config import create_midjourney_agent, create_udio_agent
from cli.src.history import PromptHistory

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
        self.current_model = "gpt-4o-2024-11-20"  # Default model
        self.prompts = {
            'midjourney': self.load_prompt('prompts/midjourney.txt'),
            'udio': self.load_prompt('prompts/udio.txt')
        }
        # Initialize agents
        self.update_agents()
        # Initialize history handler (not storing history within composer anymore)
        self.history_handler = PromptHistory()
        self.console = Console(theme=Theme({"info": "cyan", "warning": "yellow", "error": "bold red", "success": "bold green"}))
        # Define custom style once
        self.custom_style = QuestionaryStyle([
            ("question", "bold cyan"),
            ("answer", "bold green"),
            ("pointer", "bold cyan"),
            ("highlighted", "bold cyan"),
            ("selected", "bold green"),
            ('separator', 'fg:#6C6C6C'),
        ])

    def update_agents(self):
        """Update agents with the current model."""
        self.agents = {
            'midjourney': create_midjourney_agent(model=self.current_model),
            'udio': create_udio_agent(model=self.current_model)
        }

    @staticmethod
    def load_prompt(file_path: str) -> str:
        full_path = os.path.join(os.path.dirname(__file__), '..', file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Error: Prompt file not found at {full_path}", file=sys.stderr)
            return ""
        except Exception as e:
            print(f"Error reading prompt file {full_path}: {e}", file=sys.stderr)
            return ""

    async def generate_completion(self, prompt_type: str, question: str) -> str | None:
        try:
            # Calculate input tokens
            system_prompt = self.prompts[prompt_type]
            if not system_prompt:
                self.console.print(f"[error]System prompt for '{prompt_type}' is missing or empty.[/error]")
                return None
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

    def save_output(self, prompt_type: str, question: str, output: str) -> str | None:
        # Create output directory structure if it doesn't exist
        home_dir = os.path.expanduser('~')
        output_dir = os.path.join(home_dir, '.prompt-cli', 'output', prompt_type)
        os.makedirs(output_dir, exist_ok=True)

        # Create a filename based on timestamp and prompt type
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        # Keep a safe version of the question for context, but don't rely on it for uniqueness
        safe_question_prefix = "".join([c if c.isalnum() else '_' for c in question[:30]]).rstrip('_')
        filename = f"{prompt_type}_{timestamp_str}_{safe_question_prefix}.json"

        file_path = os.path.join(output_dir, filename)

        # Prepare data for JSON storage
        # --- Calculate cost info again or retrieve if stored ---
        # This assumes generate_completion returns cost info or we recalculate it here
        # For simplicity, let's assume we recalculate based on the final output
        try:
            system_prompt = self.prompts[prompt_type]
            input_tokens = count_tokens(system_prompt + question)
            output_tokens = count_tokens(output)
            price_info = calculate_prompt_price(input_tokens, output_tokens, self.current_model)
        except Exception: # Basic fallback if token counting/pricing fails
            price_info = {"error": "Could not calculate cost"}

        data_to_save = {
            "prompt_type": prompt_type,
            "model_used": self.current_model,
            "timestamp_iso": timestamp.isoformat(), # Store timestamp in ISO format
            "question": question,
            "output": output,
            "cost_info": price_info
            # Add other relevant metadata if needed
        }

        # Save data as JSON
        try:
            with open(file_path, "w", encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4) # Use indent for readability
            return file_path
        except Exception as e:
            self.console.print(f"[error]Failed to save output to {file_path}: {str(e)}[/error]")
            return None # Return None on failure

    def run(self):
        # Define constants for menu actions to avoid string comparisons
        ACTION_GEN_MIDJOURNEY = "gen_midjourney"
        ACTION_GEN_UDIO = "gen_udio"
        ACTION_VIEW_HISTORY = "view_history"
        ACTION_SWITCH_MODEL = "switch_model"
        ACTION_QUIT = "quit_app"

        while True:
            self.console.print("\n=== Prompt Generator ===", style="bold blue")
            self.console.print("[info]Use arrow keys to navigate and Enter to select:[/info]")

            # Use questionary with clearer value mapping
            choices = [
                Choice("Generate Midjourney prompts for image creation", value=ACTION_GEN_MIDJOURNEY),
                Choice("Generate Udio prompts for music creation", value=ACTION_GEN_UDIO),
                Choice("View history of previously generated prompts", value=ACTION_VIEW_HISTORY),
                Choice(f"Switch model (Current: {self.models[self.current_model]['name']})", value=ACTION_SWITCH_MODEL),
                Choice("Quit the application", value=ACTION_QUIT)
            ]

            selected_action = questionary.select(
                "Select an option:",
                choices=choices,
                style=self.custom_style
            ).ask()

            if selected_action is None: # Handle Ctrl+C
                self.console.print('\n[warning]Exiting application due to user interruption... Goodbye![/warning]')
                break

            # --- Process selected action ---
            if selected_action == ACTION_QUIT:
                self.console.print('[warning]Exiting... Goodbye![/warning]')
                break

            elif selected_action == ACTION_VIEW_HISTORY:
                history_choices = ["midjourney", "udio"]
                selected_type = questionary.select(
                    "Which history do you want to view interactively?",
                    choices=history_choices,
                    style=self.custom_style
                ).ask()

                # Handle Ctrl+C in history type selection
                if selected_type is None:
                    self.console.print('\n[warning]History selection cancelled.[/warning]')
                    continue # Go back to main menu

                if selected_type:
                    # Reuse existing history handler instance instead of creating a new one
                    self.history_handler.interactive_history(selected_type) # Use self.history_handler
                continue # Go back to main menu

            elif selected_action == ACTION_SWITCH_MODEL:
                # Use questionary.Choice for better value handling
                model_choices = [
                    Choice(f"{value['name']} - {value['description']}", value=key)
                    for key, value in self.models.items()
                ]
                # Add a Cancel option
                model_choices.append(Choice("[Cancel]", value=None))

                new_model_key = questionary.select(
                    "Select a model:",
                    choices=model_choices,
                    style=self.custom_style
                ).ask()

                if new_model_key and new_model_key in self.models:
                    self.current_model = new_model_key
                    self.update_agents()
                    self.console.print(f"[success]Switched to model: {self.models[self.current_model]['name']}[/success]")
                elif new_model_key is not None: # User selected something, but it wasn't valid (shouldn't happen with Choice)
                    self.console.print("[error]Invalid model selection.[/error]")
                # If new_model_key is None (Cancel or Ctrl+C), just continue
                continue # Go back to main menu

            elif selected_action in [ACTION_GEN_MIDJOURNEY, ACTION_GEN_UDIO]:
                prompt_type = 'midjourney' if selected_action == ACTION_GEN_MIDJOURNEY else 'udio'
                prompt_noun = 'image' if prompt_type == 'midjourney' else 'music'

                question = questionary.text(
                    f"Describe the {prompt_noun} (or type 'q' to cancel):", # Clarify 'q' action
                    style=self.custom_style
                ).ask()

                if question is None: # Handle Ctrl+C during text input
                    self.console.print('\n[warning]Input cancelled.[/warning]')
                    continue # Go back to main menu

                # Handle empty input after clarifying 'q'
                if not question:
                    self.console.print('[error]Please provide a description or type \'q\' to cancel.[/error]')
                    continue

                # Check for 'q' specifically
                if question.strip().lower() == 'q':
                    self.console.print('[warning]Generation cancelled.[/warning]')
                    continue # Go back to main menu

                # --- Generation logic ---
                with self.console.status("[bold green]Generating...[/bold green]"):
                    # Run the async function
                    output = asyncio.run(self.generate_completion(prompt_type, question))

                if output:
                    # Display and save output
                    self.console.print("\nGenerated Output:", style="bold cyan")
                    display_output = re.sub(r'\*\*(.*?)\*\*', r'\1', output) # Basic cleanup for display
                    display_output = display_output.replace('*', '')
                    self.console.print(Panel(display_output.strip(), expand=False))

                    saved_file = self.save_output(prompt_type, question, output)
                    if saved_file:
                        self.console.print(f"\n[success]Saved to: {saved_file}[/success]")

                    # --- Interactive Copy Logic ---
                    variations = re.findall(r'^\s*(\d+)\.\s*(.*?)(?=\n\s*\d+\.|\n*$)', output, re.DOTALL | re.MULTILINE)

                    copy_back_value = '__back__' # Define constant for back value

                    if variations:
                        # --- Loop for multiple copies ---
                        while True:
                            self.console.print("\n[bold yellow]Copy a variation? (or go back)[/bold yellow]")
                            variation_choices = [
                                Choice(f"{num}: {text.strip()[:60]}{'...' if len(text.strip()) > 60 else ''}", value=text.strip())
                                for num, text in variations
                            ]
                            variation_choices.append(questionary.Separator())
                            variation_choices.append(Choice("Back to Main Menu", value=copy_back_value))

                            selected_variation = questionary.select(
                                "Select variation to copy:",
                                choices=variation_choices,
                                style=self.custom_style
                            ).ask()

                            if selected_variation is None or selected_variation == copy_back_value:
                                break # Exit copy loop
                            else:
                                copy_to_clipboard(self.console, selected_variation, "Output Variation")
                        # --- End Loop ---

                    else:
                        # --- Loop for multiple copies (no variations) ---
                        # Define constants for copy actions
                        COPY_PROMPT = 'copy_prompt'
                        COPY_OUTPUT = 'copy_output'

                        while True:
                            self.console.print("\n[bold yellow]Copy output? (or go back)[/bold yellow]")
                            no_variation_choices = [
                                Choice('Copy Original Prompt', value=COPY_PROMPT),
                                Choice('Copy Full Output', value=COPY_OUTPUT),
                                Choice("Back to Main Menu", value=copy_back_value)
                            ]
                            copy_choice = questionary.select(
                                "Select an action:",
                                choices=no_variation_choices,
                                style=self.custom_style
                            ).ask()

                            if copy_choice is None or copy_choice == copy_back_value:
                                break # Exit copy loop
                            elif copy_choice == COPY_PROMPT:
                                copy_to_clipboard(self.console, question, "Original Prompt")
                            elif copy_choice == COPY_OUTPUT:
                                # Use the cleaned display_output
                                copy_to_clipboard(self.console, display_output.strip(), "Full Output")
                        # --- End Loop ---
                    # --- END ADDED ---

                # Add a newline for spacing before looping back to main menu
                self.console.print()
            else:
                # Handle cases where selected_action is not matched (should not happen with Choice)
                self.console.print(f"[error]Unknown action: {selected_action}[/error]")
                continue