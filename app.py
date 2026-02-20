from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import re
import random
from pymongo import MongoClient
from dotenv import load_dotenv   # ✅ NEW

app = Flask(__name__)
CORS(app)

# ===============================
# CONFIG (ENV BASED)
# ===============================

# ✅ Load .env file
load_dotenv()

# 🔥 Pick from environment
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Optional safety check
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY missing in .env")

if not MONGO_URI:
    raise ValueError("MONGO_URI missing in .env")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["chatbotDB"]

users_collection = db["users"]
complaints_collection = db["complaints"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

user_sessions = {}
registration_sessions = {}
complaint_sessions = {}

# ===============================
# Utility
# ===============================

def generate_complaint_id():
    return f"CMP-{random.randint(10000,99999)}"

# ===============================
# Static Files
# ===============================

@app.route("/chatbot.js")
@app.route("/chatbot.js")
def serve_js():
    widget_path = os.path.join(BASE_DIR, "widget")
    return send_from_directory(widget_path, "chatbot.js")

@app.route("/chatbot.css")
def serve_css():
    widget_path = os.path.join(BASE_DIR, "widget")
    return send_from_directory(widget_path, "chatbot.css")


@app.route("/")
def home():
    return "Backend running successfully"

# ===============================
# MAIN CHAT ROUTE
# ===============================

@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    user_message = data.get("message")
    user_id = data.get("user_id", "default")
    message_lower = user_message.lower()

    # ===== REGISTRATION FLOW =====

    if user_sessions.get(user_id) == "register_name":
        registration_sessions[user_id] = {"name": user_message}
        user_sessions[user_id] = "register_email"
        return jsonify({"reply":"📧 Please enter your email."})

    if user_sessions.get(user_id) == "register_email":
        registration_sessions[user_id]["email"] = user_message
        user_sessions[user_id] = "register_account"
        return jsonify({"reply":"🏦 Please enter your account number."})

    if user_sessions.get(user_id) == "register_account":
        registration_sessions[user_id]["account"] = user_message
        user_sessions[user_id] = "register_address"
        return jsonify({"reply":"📍 Please enter your address."})

    if user_sessions.get(user_id) == "register_address":
        registration_sessions[user_id]["address"] = user_message
        users_collection.insert_one(registration_sessions[user_id])
        user_sessions[user_id] = None
        registration_sessions[user_id] = {}
        return jsonify({"reply":"✅ Registration completed successfully!"})

    # ===== COMPLAINT FLOW =====

    if user_sessions.get(user_id) == "complaint_issue":
        complaint_sessions[user_id] = {"issue": user_message}
        user_sessions[user_id] = "complaint_email"
        return jsonify({"reply":"📧 Please provide your registered email for complaint tracking."})

    if user_sessions.get(user_id) == "complaint_email":

        email = user_message.strip().lower()
        user = users_collection.find_one({"email": email})

        if not user:
            user_sessions[user_id] = "register_name"
            return jsonify({"reply":"❌ Email not found.\n📝 Let's register you first.\nPlease enter your name."})

        complaint_id = generate_complaint_id()
        issue_text = complaint_sessions[user_id]["issue"]

        complaints_collection.insert_one({
            "complaint_id": complaint_id,
            "issue": issue_text,
            "email": email,
            "name": user.get("name","User"),
            "status": "Pending"
        })

        user_sessions[user_id] = None
        complaint_sessions[user_id] = {}

        return jsonify({
            "reply": f"""
<div class="complaint-card">
<div class="ticket-title">✅ Complaint Registered Successfully</div>

<div><b>🆔 Ticket ID:</b> {complaint_id}</div>
<div><b>👤 Name:</b> {user.get('name','User')}</div>
<div><b>📧 Email:</b> {email}</div>

<div class="issue-box">
<b>📝 Issue:</b><br>{issue_text}
</div>

<div class="status-badge">Pending</div>

<div class="ticket-note">
Our support team will contact you soon 🙂
</div>
</div>
"""
        })

    # ===== REGISTRATION KEYWORDS =====

    if any(word in message_lower for word in [
        "register","create account","new account","open account","signup","sign up"
    ]):
        user_sessions[user_id] = "register_name"
        return jsonify({"reply":"📝 Let's create your account.\nPlease enter your name."})

    # ===== COMPLAINT KEYWORDS =====

    if any(word in message_lower for word in [
        "complaint","issue","problem","support","help"
    ]):
        user_sessions[user_id] = "complaint_issue"
        return jsonify({"reply":"🛠️ Please describe your issue."})

    # ===== EMAIL FETCH =====

    email_match = re.search(r"\S+@\S+\.\S+", user_message)

    if email_match:

        email = email_match.group().lower()
        user = users_collection.find_one({"email": email})

        if user:
            account=user.get("account","")
            masked_account="XXXXXX"+account[-4:] if account else "N/A"

            return jsonify({"reply":f"""
👋 Welcome back {user.get('name','User')}

📧 {email}
🏦 {masked_account}
📍 {user.get('address','Not Available')}
"""})

        return jsonify({"reply":"❌ No account found for this email."})

    # ===== AI FALLBACK =====

    response=requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization":f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":"application/json"
        },
        json={
            "model":"openai/gpt-4o-mini",
            "messages":[
                {"role":"system","content":"You are helpful banking assistant."},
                {"role":"user","content":user_message}
            ]
        }
    )

    reply=response.json()["choices"][0]["message"]["content"]

    return jsonify({"reply":reply})

if __name__ == "__main__":
    app.run()
