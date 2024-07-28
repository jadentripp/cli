import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from dotenv import load_dotenv
from openai import AsyncOpenAI
import tiktoken

from .utils import get_video_id, get_transcript, generate_folder_name

load_dotenv()
console = Console()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"
MAX_TOKENS = 4000

def chunk_text(text: str) -> list[str]:
    encoding = tiktoken.encoding_for_model(MODEL)
    tokens = encoding.encode(text)
    chunks = []
    
    for i in range(0, len(tokens), MAX_TOKENS):
        chunk = encoding.decode(tokens[i:i + MAX_TOKENS])
        chunks.append(chunk)
    
    return chunks

async def summarize_transcript(transcript: str) -> str:
    chunks = chunk_text(transcript)
    summaries = []

    for i, chunk in enumerate(chunks):
        messages = [
            {"role": "system", "content": "Summarize the following text segment:"},
            {"role": "user", "content": chunk}
        ]
        
        response = await client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.4, max_tokens=1000
        )
        summaries.append(response.choices[0].message.content)
        console.print(f"Processed chunk {i+1}/{len(chunks)}")

    if len(summaries) > 1:
        final_summary_prompt = "\n".join(summaries)
        messages = [
            {"role": "system", "content": "Create a cohesive summary from the following segment summaries:"},
            {"role": "user", "content": final_summary_prompt}
        ]
        
        response = await client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.4, max_tokens=2000
        )
        return response.choices[0].message.content
    else:
        return summaries[0]

async def process_video(url: str) -> None:
    try:
        video_id = get_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")

        transcript = await get_transcript(video_id)
        if not transcript:
            raise ValueError("Could not retrieve transcript")
        
        summary = await summarize_transcript(transcript)
        
        console.print(Panel(Markdown(summary), title="Summary", border_style="cyan"))

        output_dir = os.path.join('output', generate_folder_name(summary))
        os.makedirs(output_dir, exist_ok=True)
        
        with open(os.path.join(output_dir, "summary.md"), 'w', encoding='utf-8') as f:
            f.write(summary)
        
        console.print(f"Summary saved in {output_dir}")
    
    except Exception as e:
        console.print(f"Error: {str(e)}")

# Main function (assuming it's defined elsewhere)
# async def main():
#     url = input("Enter YouTube URL: ")
#     await process_video(url)