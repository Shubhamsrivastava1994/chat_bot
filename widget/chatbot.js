(function(){

    // ===============================
    // Load External CSS
    // ===============================
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://chat-bot-c70y.onrender.com/chatbot.css";
    //link.href = "http://localhost:5001/chatbot.css";
    document.head.appendChild(link);

    // ===============================
    // Bubble
    // ===============================
    const bubble = document.createElement("div");
    bubble.id = "chatbot-bubble";
    bubble.innerHTML = "💬";
    document.body.appendChild(bubble);

    // ===============================
    // Chat container
    // ===============================
    const container = document.createElement("div");
    container.id = "chatbot-container";
    container.innerHTML = `
        <div id="chat-messages"></div>
        <input id="chat-input" placeholder="Type your message..." />
    `;
    document.body.appendChild(container);

    const messages = document.getElementById("chat-messages");
    const input = document.getElementById("chat-input");

    // Welcome message
    messages.innerHTML += `
    <div class="msg bot">
        <div style="font-weight:bold;font-size:15px;margin-bottom:6px;">
            👋 Welcome!
        </div>
        How can I help you today?

        <div class="welcome-card">
            📧 <b>Account Details</b><br>
            Enter your registered email ID.
        </div>

        <div class="welcome-card">
            📝 <b>Register New Account</b><br>
            Type <b>register</b>.
        </div>

        <div class="welcome-card">
            🛠️ <b>Raise Complaint</b><br>
            Describe your issue.
        </div>
    </div>
    `;

    bubble.onclick = function(){
        container.style.display =
            container.style.display === "flex" ? "none" : "flex";
    };

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    input.addEventListener("keypress", async function(e){

        if(e.key === "Enter" && input.value.trim() !== ""){

            let msg = input.value.trim();
            input.value="";

            messages.innerHTML += `<div class="msg user">${msg}</div>`;
            scrollToBottom();

            let res = await fetch("https://chat-bot-c70y.onrender.com/chat",{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({
                    message: msg,
                    user_id: "demo_user_1"
                })
            });

            let data = await res.json();

            messages.innerHTML += `<div class="msg bot">${data.reply}</div>`;
            scrollToBottom();
        }

    });

})();
