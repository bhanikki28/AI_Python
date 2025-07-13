import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents import Tool
from openai import OpenAI
from langchain.prompts import PromptTemplate

# Load environment variables    
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm_name = "gpt-3.5-turbo"

client = OpenAI(api_key=OPENAI_API_KEY)


response = client.chat.completions.create(
    model=llm_name,
    messages=[
        {
            "role": "system", "content": "You are a helpful assistant"
        },
        {
            "role": "user", "content": "who is Nelson Mandela ?"
        },
    ]
)

print(response.choices[0].message.content)