import os
from openai import AsyncOpenAI
import logging
from .utils import get_chat_completion

# Configure logging
logger = logging.getLogger(__name__)

# Initialize AsyncOpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"

async def summarize_text(transcript: str, additional_instructions: str = ""):
    logger.info("Starting text summarization")
    prompt = f"""Summarize the following transcript:

    {transcript}

    Additional instructions: {additional_instructions}

    Please provide a detailed summary that captures the main points and key details of the transcript.
    """

    try:
        logger.info("Calling OpenAI API for summary generation")
        content = await get_chat_completion([
            {"role": "system", "content": "You are an expert in summarizing complex information."},
            {"role": "user", "content": prompt}
        ], model=MODEL)
        logger.info("Summary generated successfully")
        return content
    except Exception as e:
        logger.error(f"Error in summarize_text: {str(e)}")
        raise