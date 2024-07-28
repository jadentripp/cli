import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from functools import lru_cache
import logging
import asyncio
import time
from typing import List, Optional, Tuple
from src.tokenization import tokenize

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Update OpenAI client initialization to use AsyncOpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"  # Update to use GPT-4o mini

# YouTube utilities
@lru_cache(maxsize=100)
async def get_transcript(video_id):
    logger.info(f"Fetching transcript for video ID: {video_id}")
    try:
        transcript = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, YouTubeTranscriptApi.get_transcript, video_id
            ),
            timeout=30  # 30 seconds timeout
        )
        logger.info(f"Transcript fetched successfully. Length: {len(transcript)} entries")
        full_text = ' '.join(entry['text'] for entry in transcript)
        logger.info(f"Full transcript length: {len(full_text)} characters")
        return full_text
    except asyncio.TimeoutError:
        logger.error(f"Timeout error while fetching transcript for video ID: {video_id}")
        return None
    except Exception as e:
        logger.exception(f"Error fetching transcript: {str(e)}")
        return None

def get_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed_url.path[1:]
    if parsed_url.hostname in ('youtube.com', 'www.youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        if parsed_url.path.startswith(('/embed/', '/v/')):
            return parsed_url.path.split('/')[2]
    return None

# Folder utilities
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

def generate_folder_name(summary: str) -> str:
    logger.info("Generating folder name")
    start_time = time.time()
    content = get_chat_completion([
        {"role": "system", "content": "Generate a concise, descriptive folder name based on the given summary. Use underscores instead of spaces and keep it under 50 characters."},
        {"role": "user", "content": f"Summary:\n\n{summary}"}
    ], model=MODEL)
    end_time = time.time()
    logger.info(f"Folder name generated in {end_time - start_time:.2f} seconds")
    
    return content.strip().replace(" ", "_")

# File utilities
def save_transcript(transcript, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(transcript)

def save_summary(summary, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(summary)

def chunk_on_delimiter(input_string: str, max_tokens: int, delimiter: str) -> List[str]:
    chunks = input_string.split(delimiter)
    combined_chunks, _, dropped_chunk_count = combine_chunks_with_no_minimum(
        chunks, max_tokens, chunk_delimiter=delimiter, add_ellipsis_for_overflow=True
    )
    if dropped_chunk_count > 0:
        logger.warning(f"{dropped_chunk_count} chunks were dropped due to overflow")
    combined_chunks = [f"{chunk}{delimiter}" for chunk in combined_chunks]
    return combined_chunks

def combine_chunks_with_no_minimum(
        chunks: List[str],
        max_tokens: int,
        chunk_delimiter="\n\n",
        header: Optional[str] = None,
        add_ellipsis_for_overflow=False,
) -> Tuple[List[str], List[int], int]:
    dropped_chunk_count = 0
    output = []  # list to hold the final combined chunks
    output_indices = []  # list to hold the indices of the final combined chunks
    candidate = (
        [] if header is None else [header]
    )  # list to hold the current combined chunk candidate
    candidate_indices = []
    for chunk_i, chunk in enumerate(chunks):
        chunk_with_header = [chunk] if header is None else [header, chunk]
        if len(tokenize(chunk_delimiter.join(chunk_with_header))) > max_tokens:
            logger.warning(f"Chunk overflow")
            if (
                    add_ellipsis_for_overflow
                    and len(tokenize(chunk_delimiter.join(candidate + ["..."]))) <= max_tokens
            ):
                candidate.append("...")
                dropped_chunk_count += 1
            continue  # this case would break downstream assumptions
        # estimate token count with the current chunk added
        extended_candidate_token_count = len(tokenize(chunk_delimiter.join(candidate + [chunk])))
        # If the token count exceeds max_tokens, add the current candidate to output and start a new candidate
        if extended_candidate_token_count > max_tokens:
            output.append(chunk_delimiter.join(candidate))
            output_indices.append(candidate_indices)
            candidate = chunk_with_header  # re-initialize candidate
            candidate_indices = [chunk_i]
        # otherwise keep extending the candidate
        else:
            candidate.append(chunk)
            candidate_indices.append(chunk_i)
    # add the remaining candidate to output if it's not empty
    if (header is not None and len(candidate) > 1) or (header is None and len(candidate) > 0):
        output.append(chunk_delimiter.join(candidate))
        output_indices.append(candidate_indices)
    return output, output_indices, dropped_chunk_count