
from flask import Flask, request, jsonify, render_template, url_for
import dotenv
import os
from PIL import Image
from flask_cors import CORS
import base64
from io import BytesIO
import google.generativeai as genai
import fitz  # PyMuPDF
import time
from flask_mail import Mail

#code for signup and login
import mysql.connector
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from db import get_db_connection

#for the google oauth
from authlib.integrations.flask_client import OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

#import datetime
from datetime import timedelta

#singup validation
from singupValidation import is_valid_email

#aiwriter 
from ai_writer import get_gemini_response

######### Routes #########
from routes.auth_routes import auth_routes



dotenv.load_dotenv()

app = Flask(__name__)
CORS(app)

#changes done by frontend team.
@app.after_request
def add_coop_header(response):
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    return response

#secrete key on the app
app.secret_key = os.getenv('APP_SECRET_KEY')


#google oauth2.0
# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    redirect_uri='http://localhost:5000/auth/google/callback',
    client_kwargs={'scope': 'openid profile email'}
)

# Gmail SMTP server configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587 #if ssl-465, tls-587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False  # Set to False because TLS is being used
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ID')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')  # Use app password if 2-Step Verification is enabled
app.config['MAIL_DEFAULT_SENDER'] = 'prasadthorve99@gmail.com'  # Optional: default sender email address

print("email id ", os.getenv('EMAIL_ID'))

mail = Mail(app)

# Load JWT secret key from environment variable
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

# Configure session lifetime to 10 minutes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

#for password encryption
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


############## Blue Prints here ############################3
app.register_blueprint(auth_routes)


###################  code testing ###########################



##############################################################

# Helper Functions
def get_image_base64(image_raw):
    buffered = BytesIO()
    img_format = image_raw.format if image_raw.format else 'JPEG'
    try:
        image_raw.save(buffered, format=img_format)
    except ValueError:
        image_raw.convert('RGB').save(buffered, format='JPEG')
    img_byte = buffered.getvalue()
    return base64.b64encode(img_byte).decode('utf-8')

def base64_to_image(base64_string):
    base64_string = base64_string.split(",")[1]
    return Image.open(BytesIO(base64.b64decode(base64_string)))

def pdf_to_images(pdf_file):
    images = []
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images

def messages_to_gemini(messages):
    gemini_messages = []
    prev_role = None
    for message in messages:
        if prev_role and (prev_role == message["role"]):
            gemini_message = gemini_messages[-1]
        else:
            gemini_message = {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [],
            }

        for content in message["content"]:
            if content["type"] == "text":
                gemini_message["parts"].append(content["text"])
            elif content["type"] == "image_url":
                gemini_message["parts"].append(base64_to_image(content["image_url"]["url"]))

        if prev_role != message["role"]:
            gemini_messages.append(gemini_message)

        prev_role = message["role"]
    return gemini_messages

def stream_llm_response(api_key, messages):
    response_message = ""
    response_messages = []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    gemini_messages = messages_to_gemini(messages)

    for chunk in model.generate_content(
        contents=gemini_messages,
        stream=True,
    ):
        chunk_text = chunk.text or ""
        response_message += chunk_text
        response_messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text": chunk_text}]
        })

    return response_messages

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        return jsonify({"error": "Google API Key is missing"}), 400
    
    response_messages = stream_llm_response(api_key, messages)
    return jsonify({"messages": response_messages})

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raw_img = Image.open(file)
        img_base64 = get_image_base64(raw_img)
        return jsonify({"image_url": f"data:image/jpeg;base64,{img_base64}"})
    
    elif file and file.filename.lower().endswith('.pdf'):
        images = pdf_to_images(file)
        img_urls = [f"data:image/jpeg;base64,{get_image_base64(img)}" for img in images]
        return jsonify({"image_urls": img_urls})
    
    return jsonify({"error": "Unsupported file type"}), 400

#api for ai_writer
@app.route('/api/ai_writer', methods=['POST'])
def ai_writer():
    data = request.json
    input_text = data.get('input_text')
    no_words = data.get('no_words')
    blog_style = data.get('blog_style')

    if not input_text or not no_words or not blog_style:
        return jsonify({"error": "Missing input data"}), 400

    response_text = get_gemini_response(input_text, no_words, blog_style)
    return jsonify({"generated_text": response_text})


#api for singup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return jsonify({"message": "This is the signup endpoint. Please use POST to create a new user."})
    
    elif request.method == 'POST':
        # Your signup logic for POST request
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Validate email format
        if not is_valid_email(email):
            return jsonify({"error": "Invalid email format"}), 400

        # Hash the password
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if user already exists
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            if user:
                return jsonify({"error": "User already exists"}), 400

            # Insert new user
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
            ''', (username, email, password_hash))

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({"message": "User created successfully"}), 201
        except mysql.connector.Error as err:
            return jsonify({"error - mysql connection issue": str(err)}), 500


# Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    print("\ndata : ",data)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify user
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not bcrypt.check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Create JWT token
        access_token = create_access_token(identity=user['id'])
        return jsonify({"access_token": access_token}), 200

    except mysql.connector.Error as err:
        return jsonify({"error - mysql connection issue": str(err)}), 500

# Protect Route Example
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    return jsonify({"message": f"This is a protected route. Your user ID is {current_user_id}."})


#google oauth api calls
@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback', methods=['POST'])
def google_callback():
    token = request.json.get('token')
    print("\nReceived token:", token)  # Log the token for debugging

    try:
        # Verify the token using Google's public keys
        print("\n I am in the try block...\n")
        time.sleep(5)
        id_info = id_token.verify_oauth2_token(token, google_requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
        print("\nToken verified successfully:", id_info)

        #Extract user info
        email = id_info.get('email')
        username = id_info.get('name')
        print("\nemail: ",email)
        print("\nusernaem: ",username)

        # Handle user sign-in or sign-up
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        if not user:
            cursor.execute('''
                INSERT INTO users (username, email)
                VALUES (%s, %s)
            ''', (username, email))
            conn.commit()

            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            print(user)

        cursor.close()
        conn.close()

        # Generate JWT token
        access_token = create_access_token(identity=user['email'])
        print("\n access token: ", access_token)
        return jsonify({"access_token": access_token}), 200

    except ValueError as e:
        # If the error is due to the token being used too early, retry after a small delay
        if "Token used too early" in str(e):
            time.sleep(5)  # Wait for 2 seconds
            try:
                id_info = id_token.verify_oauth2_token(token, google_requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))
                print("\n\nToken verified successfully after retry:", id_info)
                access_token = create_access_token(identity=id_info['sub'])
                print("\naccess token: ", access_token)
                return jsonify({"access_token": access_token}), 200
            except ValueError as retry_e:
                print("Retry failed:", str(retry_e))
                return jsonify({"error": "Invalid token"}), 400
        else:
            print("Token verification failed:", str(e))
            return jsonify({"error": "Invalid token"}), 400

if __name__ == '__main__':
    app.run(debug=True)