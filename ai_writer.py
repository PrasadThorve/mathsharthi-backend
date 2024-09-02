import os
import google.generativeai as gemini
from dotenv import load_dotenv

# Load the API key from the .env file
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise EnvironmentError("Google API Key not found. Please ensure it is set in the .env file.")

# Set the API key for Google Gemini
gemini.configure(api_key=API_KEY)

def get_gemini_response(input_text, no_words, blog_style):
    try:
        # Create the prompt
        prompt = f"Write a blog for {blog_style} job profile on the topic '{input_text}' within {no_words} words."

        # Call the Gemini API
        response = gemini.generate_text(
            prompt=prompt,
            temperature=0.01
        )

        # Extract the response text from the first candidate
        generated_text = response.candidates[0]['output']
        return generated_text

    except Exception as e:
        return f"An error occurred while generating the text: {str(e)}"
