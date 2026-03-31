import os;
from dotenv import load_dotenv

#load env variables from .env file
load_dotenv()


def main():
    print("Hello from lang-chain-demo!")
    openai_key = os.getenv('OPENAI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    print(openai_key)
    print(google_key)


if __name__ == "__main__":
    main()
