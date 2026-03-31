## Modules needed

    langchain
    langchain_community
    langchain-openai
    python-dotenv
    langchain-groq
    langchain-google-genai


## UV Installation (Package manager)

    https://docs.astral.sh/uv/getting-started/installation/

        -   curl -LsSf https://astral.sh/uv/install.sh | sh
        -   wget -qO- https://astral.sh/uv/install.sh | sh
        -   brew install uv


## Creating Virtual Env

    -   uv venv
    -   source .venv/bin/activate

## Install dependencies via UV package manager

    -   uv add -r requirements.txt
    -   uv add << individual_dependency>>
    -   uv add ipykernel



###  Understanding

    - model can be invoked (Stream/Batch)
        - model.stream()
        - model.batch()

    - model can be bind with tools
        - model_with_tools = model.bind_tools([get_weather])
        - model_with_tools.invoke()