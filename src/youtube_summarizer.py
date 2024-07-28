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
    key_points = []

    for i, chunk in enumerate(chunks):
        messages = [
            {"role": "system", "content": "You are a senior executive assistant tasked with extracting the most critical information from complex content. Identify key strategic points, major trends, and significant implications."},
            {"role": "user", "content": f"Analyze this text segment and extract the most important executive-level insights:\n\n{chunk}"}
        ]
        
        response = await client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.3, max_tokens=500
        )
        key_points.append(response.choices[0].message.content)
        console.print(f"Processed chunk {i+1}/{len(chunks)}")

    final_summary_prompt = "\n\n".join(key_points)
    messages = [
        {"role": "system", "content": "You are a chief strategy officer creating a concise, high-impact executive summary. Your task is to synthesize key information into a clear, actionable brief that highlights strategic implications and potential opportunities or risks."},
        {"role": "user", "content": f"Create a compelling executive summary from these key points:\n\n{final_summary_prompt}\n\nFollow these guidelines:\n1. Begin with a concise overview of the main topic and its significance.\n2. Highlight 3-5 key strategic insights or trends, focusing on their potential impact.\n3. Identify any critical challenges or opportunities revealed by the analysis.\n4. If applicable, note any contradictions or areas of uncertainty that require further investigation.\n5. Conclude with actionable recommendations or areas for strategic focus.\n6. Use clear, direct language suitable for high-level decision-makers.\n7. Limit the summary to no more than 500 words."}
    ]
    
    response = await client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.3, max_tokens=1000
    )
    return response.choices[0].message.content

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

        folder_name = await generate_folder_name(summary)
        output_dir = os.path.join('output', folder_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save summary
        summary_path = os.path.join(output_dir, "summary.md")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        # Save transcript
        transcript_path = os.path.join(output_dir, "transcript.txt")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        console.print(f"[green]Summary saved in: {summary_path}[/green]")
        console.print(f"[green]Transcript saved in: {transcript_path}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")