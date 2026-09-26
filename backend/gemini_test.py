import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=api_key)

interaction = client.interactions.create(
    model="gemini-3.8-flash",
    input="""
    You are SEPTA Guardian, an AI assistant that helps
    Philadelphia commuters reach their destinations on time.

    Explain your job in one sentence.
    """
)

print(interaction.output_text)