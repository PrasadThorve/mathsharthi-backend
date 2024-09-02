from flask import Flask, request, jsonify, render_template
import dotenv
import os
from PIL import Image
from flask_cors import CORS
import base64
from io import BytesIO
import openai
import google.generativeai as genai
import fitz  # PyMuPDF
 
# Code for signup and login
import mysql.connector
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from db import get_db_connection
 
dotenv.load_dotenv()
 
app = Flask(__name__)
CORS(app)
 
# Load JWT secret key from environment variable
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
 
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
 
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
 
def stream_llm_response(api_key, messages, model_type):
    response_messages = []
    if model_type == "openai":
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            stream=True
        )
        for chunk in response:
            if "choices" in chunk:
                for choice in chunk["choices"]:
                    chunk_text = choice["delta"].get("content", "")
                    if chunk_text:
                        response_messages.append({
                            "role": "assistant",
                            "content": [{"type": "text", "text": chunk_text}]
                        })
    elif model_type == "gemini":
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-1.5-pro")
        gemini_messages = messages_to_gemini(messages)
        for chunk in model.generate_content(contents=gemini_messages, stream=True):
            chunk_text = chunk.text or ""
            response_messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": chunk_text}]
            })
    return response_messages
 
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
 
# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')
 
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    api_key = os.getenv("API_KEY")
    model_type = data.get('model_type', 'gemini')  # Either "openai" or "gemini"
 
    if not api_key:
        return jsonify({"error": "API Key is missing"}), 400
 
    response_messages = stream_llm_response(api_key, messages, model_type)
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
 
# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return jsonify({"message": "This is the signup endpoint. Please use POST to create a new user."})
 
    elif request.method == 'POST':
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
 
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
 
if __name__ == '__main__':
    app.run(debug=True)