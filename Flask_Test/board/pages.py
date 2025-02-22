from flask import Blueprint, jsonify, request, current_app, render_template
import requests
from flask_mail import Message
from board.mail import mail

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    return render_template("pages/home.html")

@bp.route("/about")
def about():
    return render_template("pages/about.html")

@bp.route("/dashboard")
def dashboard():
    return render_template("pages/dashboard.html")

@bp.route('/fetch-data', methods=['GET'])
def fetch_data():
    url = "https://testapi.io/api/aam08331/Testapi"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
    
@bp.route('/send-data', methods=['POST'])
def send_data():
    url = "https://testapi.io/api/aam08331/Testapi"
    data = {"name": "John", "age": 30}

    try:
        response = requests.post(url, json=data, timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/carbon/<int:kiloWattHrs>', methods=['GET'])
def carbon(kiloWattHrs):
    # Constant
    tonToPounds = 2204.6

    # SRSO region
    actual = (3.94 * 10e-4)  * tonToPounds * kiloWattHrs

    return jsonify({"result": actual})

@bp.route('/send-email', methods=['POST'])
def send_email():
    data = request.get_json()
    recipient = data.get("recipient")
    subject = data.get("subject", "No Subject")
    body = data.get("body", "Hello, this is a test email!")

    if not recipient:
        return jsonify({"error": "Recipient email is required"}), 400

    msg = Message(subject=subject, sender="testingcapstonedesign@gmail.com", recipients=[recipient])
    msg.body = body

    try:
        mail.send(msg)
        return jsonify({"message": "Email sent successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500