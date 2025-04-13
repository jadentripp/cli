import os
import re
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

# Try to import pyperclip for clipboard functionality
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

class PromptHistory:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        self.console = Console()
        self.page_size = 10

    def get_history(self, prompt_type, search_term=None):
        """Get history of prompts for a specific type."""
        type_dir = os.path.join(self.output_dir, prompt_type)

        if not os.path.exists(type_dir):
            return []

        # Get all files in the directory
        try:
            files = os.listdir(type_dir)
            files = [f for f in files if f.endswith('.txt')]
        except Exception as e:
            self.console.print(f"[error]Error reading directory: {str(e)}[/error]")
            return []

        # Sort files by creation time (newest first)
        try:
            files.sort(key=lambda x: os.path.getctime(os.path.join(type_dir, x)), reverse=True)
        except Exception as e:
            self.console.print(f"[error]Error sorting files: {str(e)}[/error]")

        history_items = []
        for file in files:
            file_path = os.path.join(type_dir, file)

            # Extract timestamp from filename
            timestamp_match = re.search(r'_(\d{8}_\d{6})\.txt$', file)
            timestamp = None
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                except ValueError:
                    pass

            # Read the prompt from the file
            prompt = ""
            output = ""
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    prompt_match = re.search(r'Prompt: (.*?)\n\nOutput:', content, re.DOTALL)
                    if prompt_match:
                        prompt = prompt_match.group(1).strip()
                        output_match = re.search(r'\n\nOutput:\n(.*)$', content, re.DOTALL)
                        if output_match:
                            output = output_match.group(1).strip()
            except Exception as e:
                prompt = f"Error reading file: {str(e)}"

            # Filter by search term if provided
            if search_term and search_term.lower() not in prompt.lower():
                continue

            history_items.append({
                'file': file,
                'path': file_path,
                'timestamp': timestamp,
                'prompt': prompt,
                'output': output
            })

        return history_items

    def interactive_history(self, prompt_type):
        """Interactive history browser."""
        page = 0
        search_term = None
        history = self.get_history(prompt_type, search_term)

        if not history:
            self.console.print(f"[warning]No history found for {prompt_type}[/warning]")
            return

        while True:
            # Calculate pagination
            total_pages = (len(history) + self.page_size - 1) // self.page_size
            start_idx = page * self.page_size
            end_idx = min(start_idx + self.page_size, len(history))
            current_items = history[start_idx:end_idx]

            # Create a table for the history
            table = Table(title=f"{prompt_type.capitalize()} Prompts")
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Date", style="cyan")
            table.add_column("Prompt", style="green")

            # Add rows to the table
            for i, item in enumerate(current_items):
                idx = start_idx + i
                date_str = item['timestamp'].strftime("%Y-%m-%d %H:%M") if item['timestamp'] else "Unknown"
                # Truncate long prompts
                prompt_display = item['prompt']
                if len(prompt_display) > 60:
                    prompt_display = prompt_display[:57] + "..."

                table.add_row(str(idx + 1), date_str, prompt_display)

            # Display the table with pagination info
            self.console.clear()
            self.console.print(Panel(
                f"Showing {start_idx + 1}-{end_idx} of {len(history)} entries" +
                (f" (filtered by: '{search_term}')" if search_term else ""),
                title="History Navigation",
                style="cyan"
            ))
            self.console.print(table)

            # Display navigation options
            options = [
                "[b]ack to main menu",
                "[v]iew prompt details (e.g., v1)",
                "[c]opy prompt to clipboard (e.g., c1)",
                "[s]earch prompts",
                "[r]eset search"
            ]

            if page > 0:
                options.append("[p]revious page")
            if page < total_pages - 1:
                options.append("[n]ext page")

            self.console.print(" | ".join(options), style="bold yellow")

            # Get user input
            choice = Prompt.ask("Enter your choice")
            choice = choice.lower()

            if choice == 'b':
                break
            elif choice == 'n' and page < total_pages - 1:
                page += 1
            elif choice == 'p' and page > 0:
                page -= 1
            elif choice == 's':
                search_term = Prompt.ask("Enter search term (or leave blank to show all)")
                if not search_term.strip():
                    search_term = None
                history = self.get_history(prompt_type, search_term)
                page = 0  # Reset to first page after search
            elif choice == 'r':
                search_term = None
                history = self.get_history(prompt_type)
                page = 0  # Reset to first page
            elif choice.startswith('v'):
                try:
                    idx = int(choice[1:]) - 1
                    if 0 <= idx < len(history):
                        self.view_prompt_interactive(history[idx])
                    else:
                        self.console.print(f"[error]Invalid index: {idx+1}[/error]")
                        self.console.input("Press Enter to continue...")
                except ValueError:
                    self.console.print("[error]Invalid command. Use 'v' followed by a number (e.g., v1)[/error]")
                    self.console.input("Press Enter to continue...")
            elif choice.startswith('c'):
                try:
                    idx = int(choice[1:]) - 1
                    if 0 <= idx < len(history):
                        if CLIPBOARD_AVAILABLE:
                            try:
                                pyperclip.copy(history[idx]['prompt'])
                                self.console.print(f"[success]Copied prompt to clipboard![/success]")
                            except Exception as e:
                                self.console.print(f"[error]Error copying to clipboard: {str(e)}[/error]")
                        else:
                            self.console.print(f"[warning]Clipboard functionality not available. Install pyperclip package.[/warning]")
                    else:
                        self.console.print(f"[error]Invalid index: {idx+1}[/error]")
                    self.console.input("Press Enter to continue...")
                except ValueError:
                    self.console.print("[error]Invalid command. Use 'c' followed by a number (e.g., c1)[/error]")
                    self.console.input("Press Enter to continue...")

    def display_history(self, prompt_type, limit=10, search_term=None):
        """Display history of prompts for a specific type (non-interactive version)."""
        history = self.get_history(prompt_type, search_term)

        if not history:
            self.console.print(f"[warning]No history found for {prompt_type}[/warning]")
            return

        # Create a table for the history
        table = Table(title=f"Recent {prompt_type.capitalize()} Prompts")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Date", style="cyan")
        table.add_column("Prompt", style="green")
        table.add_column("File", style="dim")

        # Add rows to the table (limited to the specified number)
        for i, item in enumerate(history[:limit]):
            date_str = item['timestamp'].strftime("%Y-%m-%d %H:%M") if item['timestamp'] else "Unknown"
            # Truncate long prompts
            prompt_display = item['prompt']
            if len(prompt_display) > 50:
                prompt_display = prompt_display[:47] + "..."

            table.add_row(str(i + 1), date_str, prompt_display, item['file'])

        # Display the table with count information
        self.console.print(Panel(
            f"Showing {min(limit, len(history))} of {len(history)} entries" +
            (f" (filtered by: '{search_term}')" if search_term else ""),
            title="History Information",
            style="cyan"
        ))
        self.console.print(table)

        # Display usage instructions
        self.console.print("[bold yellow]To view details or interact with history, use the interactive mode:[/bold yellow]")
        self.console.print("python3 main.py --history-interactive midjourney")

    def view_prompt_interactive(self, item):
        """View a specific prompt and its output with interactive options."""
        self.console.clear()

        try:
            # Display the prompt and output
            self.console.print(Panel(f"[bold cyan]Prompt:[/bold cyan]\n{item['prompt']}", expand=False))
            self.console.print(Panel(f"[bold green]Output:[/bold green]\n{item['output']}", expand=False))

            # Display file information
            date_str = item['timestamp'].strftime("%Y-%m-%d %H:%M") if item['timestamp'] else "Unknown"
            self.console.print(f"[dim]File: {item['file']} (Created: {date_str})[/dim]")

            # Display options
            self.console.print("\n[bold yellow]Options:[/bold yellow]")
            self.console.print("[c]opy prompt to clipboard | [o]utput to clipboard | [b]ack to list")

            choice = Prompt.ask("Enter your choice").lower()

            if choice == 'c':
                if CLIPBOARD_AVAILABLE:
                    try:
                        pyperclip.copy(item['prompt'])
                        self.console.print("[success]Prompt copied to clipboard![/success]")
                    except Exception as e:
                        self.console.print(f"[error]Error copying to clipboard: {str(e)}[/error]")
                else:
                    self.console.print(f"[warning]Clipboard functionality not available. Install pyperclip package.[/warning]")
                self.console.input("Press Enter to continue...")
            elif choice == 'o':
                if CLIPBOARD_AVAILABLE:
                    try:
                        pyperclip.copy(item['output'])
                        self.console.print("[success]Output copied to clipboard![/success]")
                    except Exception as e:
                        self.console.print(f"[error]Error copying to clipboard: {str(e)}[/error]")
                else:
                    self.console.print(f"[warning]Clipboard functionality not available. Install pyperclip package.[/warning]")
                self.console.input("Press Enter to continue...")
            # 'b' or any other input returns to the list

        except Exception as e:
            self.console.print(f"[error]Error displaying prompt: {str(e)}[/error]")
            self.console.input("Press Enter to continue...")

    def view_prompt(self, prompt_type, index):
        """View a specific prompt and its output (non-interactive version)."""
        history = self.get_history(prompt_type)

        if not history:
            self.console.print(f"[warning]No history found for {prompt_type}[/warning]")
            return

        if index < 0 or index >= len(history):
            self.console.print(f"[error]Invalid history index: {index}. Valid range is 0-{len(history)-1}[/error]")
            return

        item = history[index]

        try:
            # Display the prompt and output
            self.console.print(Panel(f"[bold cyan]Prompt:[/bold cyan]\n{item['prompt']}", expand=False))
            self.console.print(Panel(f"[bold green]Output:[/bold green]\n{item['output']}", expand=False))

            # Display file information
            date_str = item['timestamp'].strftime("%Y-%m-%d %H:%M") if item['timestamp'] else "Unknown"
            self.console.print(f"[dim]File: {item['file']} (Created: {date_str})[/dim]")

            # Display copy instructions
            self.console.print("\n[bold yellow]To copy this prompt or interact with history, use the interactive mode:[/bold yellow]")
            self.console.print(f"python3 main.py --history-interactive {prompt_type}")

        except Exception as e:
            self.console.print(f"[error]Error displaying prompt: {str(e)}[/error]")
