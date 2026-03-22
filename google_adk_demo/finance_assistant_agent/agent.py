from google.adk.agents import LlmAgent
from google.adk.tools import google_search

finance_assistant_agent = LlmAgent(
    name="finance_assistant_agent",
    description="A finance assistant that can help with financial questions",
    tools=[google_search],
    model="gemini-2.5-flash"
)


root_agent = finance_assistant_agent;

