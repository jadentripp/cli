import os
import sys
import subprocess
import re
import json
from datetime import datetime
import questionary
from questionary import Style as QuestionaryStyle, Choice
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme
from rich.table import Table
from rich.prompt import Prompt
from cli.src.utils import count_tokens, calculate_prompt_price, copy_to_clipboard

class PromptHistory:
    def __init__(self):
        self.output_dir = os.path.join(os.path.expanduser('~'), '.prompt-cli', 'output')
        self.console = Console(theme=Theme({"info": "cyan", "warning": "yellow", "error": "bold red", "success": "bold green"}))
        self.page_size = 10

    def get_history(self, prompt_type: str, search_term: str | None = None) -> list[dict]:
        """Get history of prompts for a specific type from JSON files."""
        type_dir = os.path.join(self.output_dir, prompt_type)

        if not os.path.exists(type_dir):
            return []

        history_items = []
        try:
            # Get all JSON files
            files = [f for f in os.listdir(type_dir) if f.endswith('.json')]
            # Sort files based on timestamp embedded in filename (assuming format type_YYYYMMDD_HHMMSS_...)
            # This avoids reading file contents just for sorting
            files.sort(reverse=True) # Simple reverse alphabetical sort often works for timestamps
        except Exception as e:
            self.console.print(f"[error]Error listing or sorting directory {type_dir}: {str(e)}[/error]")
            return []

        for file in files:
            file_path = os.path.join(type_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Validate essential fields
                if not all(k in data for k in ["question", "output", "timestamp_iso"]):
                     self.console.print(f"[warning]Skipping malformed history file: {file} (missing essential fields)[/warning]")
                     continue

                # Filter by search term (search in question/prompt)
                if search_term and search_term.lower() not in data.get("question", "").lower():
                    continue

                # Parse timestamp
                timestamp = None
                try:
                    timestamp = datetime.fromisoformat(data["timestamp_iso"])
                except (ValueError, TypeError):
                    self.console.print(f"[warning]Could not parse timestamp in file: {file}[/warning]")
                    pass # Keep timestamp as None

                # Add filename and path for reference
                data['file'] = file
                data['path'] = file_path
                data['timestamp'] = timestamp # Add the parsed datetime object

                history_items.append(data)

            except json.JSONDecodeError:
                self.console.print(f"[warning]Skipping corrupted JSON history file: {file}[/warning]")
            except Exception as e:
                self.console.print(f"[error]Error reading history file {file}: {str(e)}[/error]")

        # Re-sort based on parsed timestamp object for accuracy (if needed, file sort might be sufficient)
        history_items.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)

        return history_items

    def interactive_history(self, prompt_type: str):
        """Interactive history browser (reads JSON)."""
        page = 0
        search_term = None
        history = self.get_history(prompt_type, search_term)

        if not history:
            self.console.print(f"[warning]No history found for {prompt_type}[/warning]")
            return

        # Define action constants
        ACTION_NEXT = 'next_page'
        ACTION_PREV = 'prev_page'
        ACTION_SEARCH = 'search'
        ACTION_RESET = 'reset_search'
        ACTION_BACK = 'back'

        while True:
            total_pages = (len(history) + self.page_size - 1) // self.page_size
            start_idx = page * self.page_size
            end_idx = min(start_idx + self.page_size, len(history))
            current_items = history[start_idx:end_idx]

            # --- REVISED: Prepare choices with actions first ---
            choices = []
            custom_style = QuestionaryStyle([
                ('question', 'bold cyan'), ('answer', 'bold green'),
                ('pointer', 'bold cyan'), ('highlighted', 'bold cyan'),
                ('selected', 'bold green'), ('separator', 'fg:#6C6C6C'),
            ])

            # Add navigation and action options
            action_choices = []
            if page > 0:
                action_choices.append(Choice(title='[p] Previous page', value=ACTION_PREV))
            if page < total_pages - 1:
                action_choices.append(Choice(title='[n] Next page', value=ACTION_NEXT))
            action_choices.append(Choice(title='[s] Search prompts', value=ACTION_SEARCH))
            if search_term:
                 action_choices.append(Choice(title='[r] Reset search', value=ACTION_RESET))
            action_choices.append(Choice(title='[b] Back to main menu', value=ACTION_BACK))
            choices.extend(action_choices)

            # Add separator if there are history items
            if current_items:
                choices.append(questionary.Separator('---- History Entries ----'))

                # Add prompt entries for the current page
                for i, item in enumerate(current_items):
                    idx = start_idx + i
                    date_str = item['timestamp'].strftime("%Y-%m-%d %H:%M") if item.get('timestamp') else "Unknown Date"
                    prompt_display = item.get('question', '<No Prompt Found>')
                    if len(prompt_display) > 70: # Adjust length as needed
                        prompt_display = prompt_display[:67] + "..."
                    # Use the index as the value to easily retrieve the full item
                    choices.append(Choice(title=f"{idx + 1}: {date_str} - {prompt_display}", value=idx))

            # --- END REVISED CHOICES ---

            # Display the table (remains largely the same, uses 'question' field)
            self.console.clear()
            self.console.print(f"{prompt_type.capitalize()} History - {start_idx + 1}-{end_idx} of {len(history)} entries" + (f" (filtered: '{search_term}')" if search_term else ""), style="cyan")
            if current_items:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="dim", width=4, justify="right")
                table.add_column("Date", style="cyan", width=16)
                table.add_column("Prompt", style="green", no_wrap=False) # Allow wrapping

                for i, item in enumerate(current_items):
                    idx = start_idx + i
                    date_str = item['timestamp'].strftime("%Y-%m-%d %H:%M") if item.get('timestamp') else "Unknown Date"
                    prompt_display = item.get('question', '<No Prompt Found>')
                    table.add_row(str(idx + 1), date_str, prompt_display)
                self.console.print(table)
            else: # Handle case where search yields no results
                self.console.print("[yellow]No matching history entries found.[/yellow]")


            selection = questionary.select(
                "Select a history entry to view/copy, or choose an action:",
                choices=choices,
                style=custom_style
            ).ask()

            if selection is None: # Handle Ctrl+C
                break # Exit history browser loop

            # --- Handle selection ---
            if isinstance(selection, int): # User selected a history entry index
                self.view_prompt_interactive(history[selection]) # Pass the full dictionary
                # Loop continues after viewing
            elif selection == ACTION_BACK:
                break
            elif selection == ACTION_NEXT and page < total_pages - 1:
                page += 1
            elif selection == ACTION_PREV and page > 0:
                page -= 1
            elif selection == ACTION_SEARCH:
                search_term_input = questionary.text(
                    "Enter search term (leave blank to show all, Ctrl+C to cancel):",
                    style=custom_style
                ).ask()
                if search_term_input is None: # Handle Ctrl+C during search input
                    continue
                search_term = search_term_input.strip()
                if not search_term:
                    search_term = None
                # Reset history and page when searching
                history = self.get_history(prompt_type, search_term)
                page = 0
                # No need for extra check here, loop will display empty message if needed
            elif selection == ACTION_RESET:
                search_term = None
                history = self.get_history(prompt_type)
                page = 0

    def view_prompt_interactive(self, item: dict):
        """View a specific prompt and its output from history data with interactive options."""
        try:
            # Extract data using .get for safety
            prompt = item.get('question', '<Prompt not found>')
            output = item.get('output', '<Output not found>')
            file_name = item.get('file', '<Unknown file>')
            timestamp = item.get('timestamp') # Already a datetime object or None
            date_str = timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else "Unknown Date"

            # Display prompt and file info
            self.console.clear()
            self.console.print("[bold cyan]Prompt:[/bold cyan]")
            self.console.print(prompt)

            # Clean output for display (same logic as before)
            display_output = re.sub(r'\*\*(.*?)\*\*', r'\1', output)
            display_output = display_output.replace('*', '')

            # Find variations (same logic as before)
            variations = re.findall(r'^\s*(\d+)\.\s*(.*?)(?=\n\s*\d+\.|\n*$)', output, re.DOTALL | re.MULTILINE)

            custom_style = QuestionaryStyle([
                ('question', 'bold yellow'), ('answer', 'bold green'),
                ('pointer', 'bold cyan'), ('highlighted', 'bold cyan'),
                ('selected', 'bold green'), ('separator', 'fg:#6C6C6C'),
            ])
            back_value = '__back__'

            if variations:
                self.console.print("[bold green]Output Variations:[/bold green]")
                self.console.print(display_output.strip())
                # Track the current selection index to maintain position
                current_index = 0
                while True:
                    self.console.print("\n[bold yellow]Select output variation to copy or go back:[/bold yellow]")
                    variation_choices = [
                        Choice(f"{num}: {text.strip()[:70]}{'...' if len(text.strip()) > 70 else ''}", value=(i, text.strip()))
                        for i, (num, text) in enumerate(variations)
                    ]
                    variation_choices.append(questionary.Separator())
                    variation_choices.append(Choice("Back to History List", value=back_value))

                    # Create a new questionary instance each time with the current index
                    question = questionary.select(
                        "Which variation to copy?",
                        choices=variation_choices,
                        style=custom_style,
                        default=variation_choices[current_index].value if current_index < len(variations) else None
                    )
                    selected_variation = question.ask()

                    if selected_variation is None or selected_variation == back_value:
                        break
                    else:
                        # selected_variation is now a tuple of (index, text)
                        index, text = selected_variation
                        copy_to_clipboard(self.console, text, show_success=False)
                        # Update the current index to maintain position
                        current_index = index
                        # Clear the console to reduce clutter
                        self.console.clear()
                        # Re-display the panel with the output
                        self.console.print("[bold green]Output Variations:[/bold green]")
                        self.console.print(display_output.strip())
            else:
                # No variations found
                self.console.print("[bold green]Output:[/bold green]")
                self.console.print(display_output.strip())

                # Define constants for copy actions
                COPY_PROMPT = 'copy_prompt'
                COPY_OUTPUT = 'copy_output'

                while True:
                    self.console.print("\n[bold yellow]Options:[/bold yellow]")
                    no_variation_choices = [
                        Choice('Copy Prompt', value=COPY_PROMPT),
                        Choice('Copy Full Output', value=COPY_OUTPUT),
                        Choice('Back to History List', value=back_value)
                    ]
                    choice = questionary.select(
                        "Select an action:",
                        choices=no_variation_choices, style=custom_style
                    ).ask()

                    if choice is None or choice == back_value:
                        break
                    elif choice == COPY_PROMPT:
                        copy_to_clipboard(self.console, prompt, show_success=False) # Use prompt variable
                        # Clear the console to reduce clutter
                        self.console.clear()
                        # Re-display the panel with the output
                        self.console.print("[bold green]Output:[/bold green]")
                        self.console.print(display_output.strip())
                    elif choice == COPY_OUTPUT:
                        copy_to_clipboard(self.console, display_output.strip(), show_success=False) # Use cleaned output
                        # Clear the console to reduce clutter
                        self.console.clear()
                        # Re-display the panel with the output
                        self.console.print("[bold green]Output:[/bold green]")
                        self.console.print(display_output.strip())

            # Implicit return after loop breaks

        except Exception as e:
            # More specific error message if possible
            self.console.print(f"[error]Error displaying history item {item.get('file', '')}: {type(e).__name__} - {str(e)}[/error]", style="bold red")
            self.console.input("Press Enter to return to history list...")

    def view_prompt(self, prompt_type: str, index: int):
        """View a specific prompt and its output (non-interactive version, reads JSON)."""
        history = self.get_history(prompt_type)

        if not history:
            self.console.print(f"[warning]No history found for {prompt_type}[/warning]")
            return

        # Adjust index to be 1-based for user input, convert to 0-based for list access
        if index < 1 or index > len(history):
             self.console.print(f"[error]Invalid history index: {index}. Please use a number between 1 and {len(history)}.[/error]")
             return
        item = history[index - 1] # Use 0-based index

        try:
            # Extract data using .get for safety
            prompt = item.get('question', '<Prompt not found>')
            output = item.get('output', '<Output not found>')
            file_name = item.get('file', '<Unknown file>')
            timestamp = item.get('timestamp')
            date_str = timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else "Unknown Date"

            # Display the prompt and output (using cleaned output)
            self.console.print("[bold cyan]Prompt:[/bold cyan]")
            self.console.print(prompt)
            display_output = re.sub(r'\*\*(.*?)\*\*', r'\1', output)
            display_output = display_output.replace('*', '')
            display_output = re.sub(r'\n{3,}', '\n\n', display_output) # Clean extra newlines
            self.console.print("[bold green]Output:[/bold green]")
            self.console.print(display_output.strip())

            # Update help text
            self.console.print("\n[bold yellow]To copy variations or interact further, use the interactive mode from the main menu.[/bold yellow]")

        except Exception as e:
            self.console.print(f"[error]Error displaying prompt index {index}: {str(e)}[/error]")
