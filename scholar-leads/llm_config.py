from crewai import LLM
import os
from dotenv import load_dotenv

load_dotenv()

llm = LLM(
    model = os.getenv("OPENAI_MODEL"),
    api_key = os.getenv("OPENAI_API_KEY")
)
