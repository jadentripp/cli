# Prompt History Feature

This feature allows you to view the history of previously generated prompts in the Prompt CLI application.

## Using the History Feature

### Interactive Menu

Access the history feature from within the interactive menu:

1. Start the application: `python3 main.py`
2. When prompted for a choice, enter `h` to view history
3. Select the prompt type (Midjourney or Udio)
4. The application will display the interactive history browser

## Features

### Basic Features
- View a list of previously generated prompts
- See when each prompt was created
- View the full content of specific prompts
- Sort by most recent first

### Enhanced Features
- **Numbered Entries**: Each prompt is numbered for easy reference
- **Interactive Viewing**: View full prompt details by selecting a number
- **Simple Navigation**: Easy to use interface with clear instructions
- **Detailed Information**: See both the prompt and its generated output

## Implementation Details

The history feature works by reading the saved output files in the `output/` directory. It does not modify any existing files and is completely read-only.

### Files

- `src/history.py`: Contains the `PromptHistory` class that handles reading and displaying prompt history
- `main.py`: Updated to include command-line arguments for accessing history
- `src/prompt_composer.py`: Updated to include an interactive history option

### Classes

#### PromptComposer

- `view_history(prompt_type)`: Displays a table of recent prompts and allows viewing details

The history feature is fully integrated into the Terminal User Interface (TUI) for a seamless experience.
