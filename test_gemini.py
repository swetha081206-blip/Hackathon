import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: API key not found.")
else:
    try:
        client = genai.Client(api_key=api_key)

        response = client.interactions.create(
            model="gemini-3.8-flash",
            input="Reply with exactly: Gemini API connection successful."
        )

        print("Success! Gemini API is working.")
        print(response.output_text)

    except Exception as e:
        print("Gemini API test failed.")
        print(type(e).__name__, str(e))
