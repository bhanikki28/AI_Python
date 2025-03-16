
# Install the following Modules

    pip install flask
    pip install flask_cors


# Setting up Python Virtual Environment

    python3 -m venv chat_gpt_env
    source chat_gpt_env/bin/activate


    pip freeze -l > requirements.txt 


# LLM

    LLM - LargeLanguageModel
    LLM acts as transformer to understand the input and generates the output
    Models Used
        - GPT-2 for text generation
        - GPT-3 for text generation

        - BERT for sentiment analysis
        - T5 for Language Translation


    ChatGPT using Python with OpenSource LLMs and Hugging Face

# Code Documentation

    You import the Flask class from the flask module.
    You create an instance of the Flask class and assign it to the variable app.
    You define a route for the homepage by decorating the home() function with the @app.route() decorator. The function returns the string 'Hello, World!'. This means that when the user visits the URL where the website is hosted, the backend server will receive the request and return 'Hello, World!' to the user.
    The if __name__ == '__main__': condition ensures that the server is only run if the script is executed directly, not when imported as a module.
    Finally, you call app.run() to start the server.