from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from utils.helper_funtions import generate_otp
from flask import session


auth_routes = Blueprint('auth_routes', __name__)

#write your apis here
#test api not used in the application
@auth_routes.route('/test_auth', methods=['GET'])
def write_something():
    return jsonify({"message": "hii... This route is running!"}), 200


#API for the testing if the mail server is working or not
@auth_routes.route('/send_email', methods=['POST'])
def send_email():
    try:
        from app import mail #importing here to avoid circular import
        print("trying.....")
        email = request.json.get('email')
        subject = "Test Email"
        body = "This is a test email sent from Flask using Gmail SMTP."

        msg = Message(subject, recipients=[email])
        msg.body = body
        mail.send(msg)

        return jsonify({"message": "Email sent successfully!"}), 200
    except Exception as e:
        return jsonify({"message": f"Failed to send email. Error: {str(e)}"}), 500
    
    
#api to send otp
@auth_routes.route('/send_otp', methods=['POST'])
def send_otp():
    from app import mail
    data = request.json
    email = data.get('email')
    subject = "Verification Mail for MathSharthi Application"
    
    # Generate OTP
    otp = generate_otp()
    print("\notp: ", otp)

    # Send OTP via email
    msg = Message(subject, recipients=[email])
    msg.body = f'Your OTP code is {otp}. Please use this to verify your email address.'

    try:
        mail.send(msg)
        # Store the OTP in session or a temporary database table for later verification
        session.permanent = True
        session['otp'] = otp
        session['email'] = email
        return jsonify({"message": "OTP sent successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to send OTP. Error: {str(e)}"}), 500