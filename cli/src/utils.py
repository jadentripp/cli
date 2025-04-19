import os
import sys
import subprocess
from dotenv import load_dotenv
from openai import AsyncOpenAI
import logging
import tiktoken
import asyncio
import json
from cli.src.tokenization import num_tokens_from_messages
from agents import Runner

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Update OpenAI client initialization to use AsyncOpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

async def get_chat_completion(messages, model='gpt-4o-mini'):
    logger.info(f"Calling OpenAI API with model: {model}")
    try:
        # Traditional OpenAI API approach
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )
        logger.info("OpenAI API call completed successfully")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        raise

async def get_agent_completion(agent, user_input):
    logger.info(f"Running agent: {agent.name}")
    try:
        # Use the Runner from the Agents SDK to run the agent
        result = await Runner.run(agent, input=user_input)
        logger.info("Agent run completed successfully")
        return result.final_output
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        raise

def count_tokens(text, model="gpt-4o-mini"):
    """Count the number of tokens in a text string."""
    try:
        # GPT-4o Mini uses the same tokenizer as GPT-4
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        return 0

def calculate_prompt_price(input_tokens, output_tokens, model="gpt-4o-mini"):
    """Calculate the price for a prompt based on token count."""
    # Pricing rates for different models
    prices = {
        "gpt-4o-mini": {
            "input": 0.15 / 1_000_000,  # $0.15 per 1M tokens
            "output": 0.60 / 1_000_000,  # $0.60 per 1M tokens
        },
        "gpt-4o": {
            "input": 5.00 / 1_000_000,  # $5.00 per 1M tokens
            "output": 15.00 / 1_000_000,  # $15.00 per 1M tokens
        },
        "gpt-4.5-preview": {
            "input": 75.00 / 1_000_000,  # $75.00 per 1M tokens
            "output": 150.00 / 1_000_000,  # $150.00 per 1M tokens
        },
        "gpt-4.1-2025-04-14": {
            "input": 3.00 / 1_000_000,  # $3.00 per 1M tokens
            "output": 12.00 / 1_000_000,  # $12.00 per 1M tokens
        }
    }

    if model not in prices:
        model = "gpt-4o-mini"  # default to GPT-4o Mini pricing

    input_price = input_tokens * prices[model]["input"]
    output_price = output_tokens * prices[model]["output"]
    total_price = input_price + output_price

    return {
        "input_cost": round(input_price, 6),  # Increased decimal places for smaller numbers
        "output_cost": round(output_price, 6),
        "total_cost": round(total_price, 6),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }

def copy_to_clipboard(console, text):
    """Helper function to copy text to clipboard with error handling."""
    try:
        # Lazy import pyperclip only if needed
        pyperclip = None
        if sys.platform == 'darwin':  # macOS
            try:
                # Use pbcopy on macOS
                process = subprocess.Popen(['echo', text], stdout=subprocess.PIPE)
                copy_process = subprocess.Popen(['pbcopy'], stdin=process.stdout, stderr=subprocess.PIPE)
                process.stdout.close()  # Allow process to receive a SIGPIPE if copy_process exits
                _, stderr = copy_process.communicate()
                success = copy_process.returncode == 0
                if not success:
                     console.print(f"[warning]pbcopy failed (stderr: {stderr.decode()}). Trying pyperclip...[/warning]")
                     # Fall back to pyperclip if pbcopy fails
                     import pyperclip
                     pyperclip.copy(text)
                     success = True
            except FileNotFoundError:
                 console.print("[warning]pbcopy not found. Trying pyperclip...[/warning]")
                 import pyperclip
                 pyperclip.copy(text)
                 success = True
            except subprocess.SubprocessError as e:
                console.print(f"[error]Error using pbcopy: {str(e)}. Trying pyperclip...[/error]")
                import pyperclip
                pyperclip.copy(text)
                success = True
        else:
            # For other platforms, use pyperclip
            try:
                import pyperclip
                pyperclip.copy(text)
                success = True
            except ImportError:
                 console.print("[error]pyperclip module not found. Cannot copy to clipboard.[/error]")
                 console.print("[info]Please install it: pip install pyperclip[/info]")
                 success = False
            except Exception as e:
                 console.print(f"[error]Error using pyperclip: {str(e)}[/error]")
                 success = False

        if success:
            # Success message removed to reduce UI clutter
            return True

    except Exception as e:
        # Catch any other unexpected errors
        console.print(f"[error]Unexpected error copying to clipboard: {str(e)}[/error]")
        if sys.platform == 'darwin':
            console.print("[info]If on macOS, try running: chmod +x /usr/bin/pbcopy[/info]")
        console.print("[info]If using X11, try installing xclip or xsel: sudo apt install xclip[/info]")
        console.print("[info]Alternatively, ensure pyperclip is installed: pip install pyperclip[/info]")
    return False