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

async def debug_agent():
    try:
        # Create a simple test agent
        agent = Agent(
            name="Debug Agent",
            instructions="You are a helpful assistant that provides concise responses.",
            model="gpt-4o-mini",
            model_settings=ModelSettings(
                temperature=0
            )
        )
        
        # Print agent configuration
        print(f"Agent name: {agent.name}")
        print(f"Agent model: {agent.model}")
        print(f"Agent model_settings: {agent.model_settings}")
        
        # Run the agent
        print("\nRunning agent...")
        result = await Runner.run(agent, input="Hello, can you tell me what the OpenAI Agents SDK is?")
        
        # Print the result
        print("\nAgent Response:")
        print(result.final_output)
        
    except Exception as e:
        print(f"Error: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_agent())
