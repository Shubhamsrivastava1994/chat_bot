from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import re
import random
from pymongo import MongoClient
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# ===============================
# CONFIG
# ===============================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["chatbotDB"]

users_collection = db["users"]
complaints_collection = db["complaints"]
sessions_collection = db["sessions"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===============================
# SESSION HELPERS
# ===============================

def get_session(user_id):
    return sessions_collection.find_one({"user_id": user_id})

def set_session(user_id, state, data=None):
    sessions_collection.update_one(
        {"user_id": user_id},
        {"$set": {"state": state, "data": data or {}}},
        upsert=True
    )

def clear_session(user_id):
    sessions_collection.delete_one({"user_id": user_id})

def generate_complaint_id():
    return f"CMP-{random.randint(10000,99999)}"

# ===============================
# RESET SESSION
# ===============================

@app.route("/reset-session", methods=["POST"])
def reset_session():
    data = request.json
    user_id = data.get("user_id")
    clear_session(user_id)
    return jsonify({"status":"session cleared"})

# ===============================
# STATIC
# ===============================

@app.route("/chatbot.js")
def serve_js():
    return send_from_directory(os.path.join(BASE_DIR,"widget"),"chatbot.js")

@app.route("/chatbot.css")
def serve_css():
    return send_from_directory(os.path.join(BASE_DIR,"widget"),"chatbot.css")

@app.route("/")
def home():
    return "Backend running successfully"

# ===============================
# CHAT ROUTE
# ===============================

@app.route("/chat", methods=["POST"])
def chat():

    data=request.json
    user_message=data.get("message","")
    user_id=data.get("user_id","default")
    message_lower=user_message.lower()

    session=get_session(user_id)

    # ===== REGISTRATION FLOW =====

    if session and session["state"]=="register_name":
        set_session(user_id,"register_email",{"name":user_message})
        return jsonify({"reply":"📧 Please enter your email address."})

    if session and session["state"]=="register_email":
        s=session["data"]
        s["email"]=user_message
        set_session(user_id,"register_account",s)
        return jsonify({"reply":"🏦 Please enter your account number."})

    if session and session["state"]=="register_account":
        s=session["data"]
        s["account"]=user_message
        set_session(user_id,"register_address",s)
        return jsonify({"reply":"📍 Please enter your address."})

    if session and session["state"]=="register_address":
        s=session["data"]
        s["address"]=user_message
        users_collection.insert_one(s)
        clear_session(user_id)

        return jsonify({"reply":"""
🎉 <b>Registration Successful!</b><br>
Your account has been created successfully 🙂
"""})

    # ===== COMPLAINT FLOW =====

    if session and session["state"]=="complaint_issue":
        set_session(user_id,"complaint_email",{"issue":user_message})
        return jsonify({"reply":"📧 Enter registered email for complaint tracking."})

    if session and session["state"]=="complaint_email":

        email=user_message.lower()
        user=users_collection.find_one({"email":email})

        if not user:
            set_session(user_id,"register_name")
            return jsonify({"reply":"❌ Email not found. Enter your name to register."})

        issue=session["data"]["issue"]
        cid=generate_complaint_id()

        complaints_collection.insert_one({
            "complaint_id":cid,
            "issue":issue,
            "email":email,
            "status":"Pending"
        })

        clear_session(user_id)

        return jsonify({"reply":f"""
<div class="ticket-card">

<div class="ticket-header">🎫 Complaint Registered Successfully</div>

<div class="ticket-row">🆔 <b>Ticket ID:</b> {cid}</div>
<div class="ticket-row">📧 <b>Email:</b> {email}</div>
<div class="ticket-row">📌 <b>Status:</b> <span class="status-badge">Pending</span></div>

<div class="ticket-note">
Our support team will contact you soon 🙂
</div>

</div>
"""})

    # ===== KEYWORDS =====

    if "register" in message_lower:
        set_session(user_id,"register_name")
        return jsonify({"reply":"📝 Let's create your account. Enter your name."})

    if any(x in message_lower for x in ["complaint","issue","problem"]):
        set_session(user_id,"complaint_issue")
        return jsonify({"reply":"🛠️ Please describe your issue."})

    # ===== ACCOUNT DETAILS KEYWORDS (ADDED) =====

    account_keywords = [
        "account","account details","show account","check account",
        "account info","account information","my account","account status",
        "profile","my profile","my details","customer details",
        "user details","bank details","account summary","view account",
        "show profile","show my account","show my details",
        "account overview","view my profile","display account"
    ]

    if any(keyword in message_lower for keyword in account_keywords):
        return jsonify({"reply":"""
<div class="card-box">

<div class="card-title">👤 Account Information</div>

🔐 For security reasons, please enter your <b>registered email address</b>.

I will fetch your account details instantly 🙂

</div>
"""})

    # ===== EMAIL FETCH (Beautiful Card) =====

    email_match=re.search(r"\S+@\S+\.\S+",user_message)

    if email_match:

        email=email_match.group().lower()
        user=users_collection.find_one({"email":email})

        if user:

            account=user.get("account","")
            masked="XXXXXX"+account[-4:] if account else "N/A"

            return jsonify({"reply":f"""
<div class="card-box">

<div class="card-title">👋 Account Details</div>

<div class="card-row">👤 <b>Name:</b> {user.get('name','User')}</div>
<div class="card-row">📧 <b>Email:</b> {email}</div>
<div class="card-row">🏦 <b>Account:</b> {masked}</div>
<div class="card-row">📍 <b>Address:</b> {user.get('address','Not Available')}</div>

<div class="card-footer">✅ Verified Customer</div>

</div>
"""})

        return jsonify({"reply":"❌ No account found."})

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
                {"role":"system","content":"You are professional banking assistant."},
                {"role":"user","content":user_message}
            ]
        }
    )

    reply=response.json()["choices"][0]["message"]["content"]

    return jsonify({"reply":reply})


if __name__=="__main__":
    app.run()
