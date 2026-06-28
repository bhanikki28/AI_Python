
### Setting up Virtual Env and Activate

    uv init
    uv add langchain
    uv add python-dotenv
    uv add langchain-huggingface


### Load Env Variable

   uv add python-dotenv
   import os
   from dotenv import load_dotenv
   load_dotenv()
   api_key = os.getenv("KEY_NAME")  


###  Get HuggingFace Key

    https://huggingface.co/settings/tokens



### Configure the HuggingFace, ChatHugging Face Endpoint


### Running the Agent

   uv run main.py


