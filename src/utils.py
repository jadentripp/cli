import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import logging
import tiktoken

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Update OpenAI client initialization to use AsyncOpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

async def get_chat_completion(messages, model='gpt-4o-mini'):
    logger.info(f"Calling OpenAI API with model: {model}")
    try:
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