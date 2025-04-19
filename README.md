# AI Prompt Generator CLI

A command-line interface tool for generating AI prompts for different platforms using the OpenAI Agents SDK.

## Features

- Generate Midjourney v7 prompts for image creation
- Generate Udio v1.5 prompts for music creation
- Uses OpenAI Agents SDK for improved agent-based interactions
- Modern Terminal User Interface (TUI) with arrow key navigation
- History feature to view previously generated prompts
- Saves generated prompts to files for easy reference
- Displays token usage and cost information

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the CLI application:

```bash
python main.py
```

### Interactive Navigation

The application uses arrow key navigation for a better user experience:

1. Use the **up/down arrow keys** to navigate through options
2. Press **Enter** to select an option
3. Type your prompt description when prompted
4. View the generated results

### History Feature

Access the history feature to view previously generated prompts:

- From the main menu, select "View history of previously generated prompts"
- Use arrow keys to select which prompt type to view
- Navigate through the list of previous prompts
- Select a prompt to view its details

The history feature provides a fully interactive experience within the application, with no need for command-line arguments.

### Testing the Agents SDK

To verify that the OpenAI Agents SDK is working correctly, you can run the test script:

```bash
python test_agents.py
```

This will create a simple agent and run it with a test prompt to ensure everything is configured correctly.

## How It Works

This application uses the OpenAI Agents SDK to create specialized agents for different prompt generation tasks. The agents are configured with specific instructions and can be extended with additional tools and capabilities.

## Project Structure

- `main.py`: Entry point for the CLI application
- `src/prompt_composer.py`: Main class for handling prompt generation
- `src/agents_config.py`: Configuration for OpenAI Agents
- `src/utils.py`: Utility functions for API calls and token counting
- `src/history.py`: History feature implementation
- `prompts/`: Directory containing system prompts for different platforms
- `output/`: Directory where generated prompts are saved

## Requirements

- Python 3.8+
- OpenAI API key
- Dependencies listed in requirements.txt
