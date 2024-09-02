import re
import requests
import os

# Define a function to validate email format using regex
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

# Optionally, define a function to check if the email exists using an external API
def verify_email(email):
    api_key = os.getenv('EMAIL_VERIFICATION_API_KEY')
    response = requests.get(f"https://api.emailverification.com/verify?email={email}&apikey={api_key}")
    
    if response.status_code == 200:
        result = response.json()
        return result.get('status') == 'valid'
    return False