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
       
        # Create the content parts for the model
        content_parts = [{"text": prompt}]
 
        # Use the generative model
        model = gemini.GenerativeModel(model_name="gemini-1.5-flash")
 
        response_message = ""
        response_messages = []
 
        # Generate the content and handle streaming
        for chunk in model.generate_content(
            contents=content_parts,
            stream=True,  # Streaming mode to handle large responses in chunks
        ):
            chunk_text = chunk.text or ""
            response_message += chunk_text
            response_messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": chunk_text}]
            })
 
        # Return the entire response
        return response_message
 
    except Exception as e:
        return f"An error occurred while generating the text: {str(e)}"
 
# Example usage
input_text = "AI in Healthcare"
no_words = 500
blog_style = "Data Scientist"
 
result = get_gemini_response(input_text, no_words, blog_style)
print(result)
 
 