(function(){

    // ===============================
    // USER ID
    // ===============================

    let user_id = localStorage.getItem("chat_user");

    if(!user_id){
        user_id = crypto.randomUUID();
        localStorage.setItem("chat_user", user_id);
    }

    // ===============================
    // Load CSS
    // ===============================

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://chat-bot-c70y.onrender.com/chatbot.css"
    //link.href = "http://localhost:5000/chatbot.css";
    document.head.appendChild(link);

    // ===============================
    // Bubble
    // ===============================

    const bubble = document.createElement("div");
    bubble.id = "chatbot-bubble";
    bubble.innerHTML = "💬";
    document.body.appendChild(bubble);

    // ===============================
    // Container
    // ===============================

    const container = document.createElement("div");
    container.id = "chatbot-container";
    container.style.display = "none"; // IMPORTANT
    container.innerHTML = `
        <div id="chat-messages"></div>
        <input id="chat-input" placeholder="Type your message..." />
    `;
    document.body.appendChild(container);

    const messages = document.getElementById("chat-messages");
    const input = document.getElementById("chat-input");

    // ===============================
    // Welcome Message
    // ===============================

    function showWelcome(){

        messages.innerHTML = `
        <div class="msg bot">
            👋 Welcome! How can I help you today?
            <div class="welcome-card">📧 Enter email for account details</div>
            <div class="welcome-card">📝 Type register</div>
            <div class="welcome-card">🛠️ Describe your issue</div>
        </div>
        `;
    }

    // ===============================
    // Toggle Bubble
    // ===============================

    bubble.addEventListener("click", async function(){

        const isOpen = container.style.display === "flex";

        if(isOpen){

            // 🔥 CLOSE CHAT

            container.style.display = "none";

            // reset backend session
            await fetch("https://chat-bot-c70y.onrender.com/reset-session",{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({ user_id })
            });

            // reset frontend
            messages.innerHTML = "";

            user_id = crypto.randomUUID();
            localStorage.setItem("chat_user", user_id);

        }else{

            // 🔥 OPEN CHAT

            container.style.display = "flex";
            showWelcome();
        }

    });

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    // ===============================
    // SEND MESSAGE
    // ===============================

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
                    user_id: user_id
                })
            });

            let data = await res.json();

            messages.innerHTML += `<div class="msg bot">${data.reply}</div>`;
            scrollToBottom();
        }

    });

})();
