import os
from dotenv import load_dotenv
load_dotenv()
from langchain_huggingface import HuggingFaceEndpoint,ChatHuggingFace
from langchain_core.messages import HumanMessage

#Retrieve variables safely
api_key = os.getenv("HUGGINGFACEHUB_API_TOKEN")

def main():
    print("Hello from simple-question-demo!")
    print(f"API Key Loaded : {api_key}")
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = api_key

    raw_llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    provider="together",
    task="conversational", 
    max_new_tokens=100,
    temperature=0.7,
    )

    # 3. Wrap inside ChatHuggingFace to resolve the task conflict
    chat_model = ChatHuggingFace(llm=raw_llm)

    # 4. Invoke using a Structured Message List (Required for conversational tasks)
    messages = [
        HumanMessage(content="Write a haiku about writing clean code.")
    ]

    response = chat_model.invoke(messages)

    # 5. Access the output text via .content
    print("Response:\n", response.content)

if __name__ == "__main__":
    main()
