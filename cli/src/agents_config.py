from openai import AsyncOpenAI
import os
from cli.src.utils import count_tokens
from dotenv import load_dotenv
from agents import Agent, ModelSettings

# Load environment variables from .env file
load_dotenv()

# Use the API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def load_prompt(file_path):
    """Load a prompt from a file."""
    pkg_dir = os.path.dirname(__file__)
    full_path = os.path.join(pkg_dir, '..', file_path)
    with open(full_path, 'r') as file:
        return file.read()

# Create agents for different prompt types
def create_midjourney_agent(model="gpt-4o-mini"):
    """Create an agent for Midjourney prompt generation."""
    system_prompt = load_prompt('prompts/midjourney.txt')

    # Note: Midjourney v7's Draft mode is selected in the UI and not relevant to include in the prompt itself.
    return Agent(
        name="Midjourney Prompt Generator",
        instructions=system_prompt,
        model=model,
        model_settings=ModelSettings(
            temperature=0
        ),
        mcp_config={"convert_schemas_to_strict": True}
    )

def create_udio_agent(model="gpt-4o-mini"):
    """Create an agent for Udio prompt generation."""
    system_prompt = load_prompt('prompts/udio.txt')

    return Agent(
        name="Udio Prompt Generator",
        instructions=system_prompt,
        model=model,
        model_settings=ModelSettings(
            temperature=0
        ),
        mcp_config={"convert_schemas_to_strict": True}
    )

def create_suno_agent(model="gpt-4o-mini"):
    """Create an agent for Suno AI prompt generation."""
    system_prompt = load_prompt('prompts/suno.txt')

    return Agent(
        name="Suno AI Prompt Generator",
        instructions=system_prompt,
        model=model,
        model_settings=ModelSettings(
            temperature=0
        ),
        mcp_config={"convert_schemas_to_strict": True}
    )
