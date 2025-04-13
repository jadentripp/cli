import asyncio
import os
from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings

# Load environment variables from .env file
load_dotenv()

# Check for OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please check your .env file.")

async def test_agent():
    # Create a simple test agent
    agent = Agent(
        name="Test Agent",
        instructions="You are a helpful assistant that provides concise responses.",
        model="gpt-4o-mini",
        model_settings=ModelSettings(
            temperature=0
        )
    )

    # Run the agent
    result = await Runner.run(agent, input="Hello, can you tell me what the OpenAI Agents SDK is?")

    # Print the result
    print("\nAgent Response:")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(test_agent())
