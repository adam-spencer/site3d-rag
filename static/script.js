const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const authModal = document.getElementById('auth-modal');
const mainChat = document.getElementById('main-chat');
const authSubmit = document.getElementById('auth-submit');
const authInput = document.getElementById('auth-input');

let systemPassword = "";

function unlockChat() {
    const pwd = authInput.value.trim();
    if (pwd) {
        systemPassword = pwd;
        authModal.style.display = 'none';
        mainChat.style.display = 'flex';
    }
}

authSubmit.addEventListener('click', unlockChat);
authInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') unlockChat();
});

function scrollToBottom() {
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message`;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (role === 'ai') {
        contentDiv.innerHTML = marked.parse(text);
    } else {
        contentDiv.textContent = text;
    }
    
    msgDiv.appendChild(contentDiv);
    chatBox.appendChild(msgDiv);
    scrollToBottom();
}

function showTyping() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message typing-container';
    msgDiv.innerHTML = `
        <div class="message-content typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatBox.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

function removeTyping(element) {
    if (element && element.parentNode) {
        element.parentNode.removeChild(element);
    }
}

async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;
    
    userInput.value = '';
    appendMessage('user', text);
    
    // Create the AI message container early
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message';
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Add an initial pulsing status
    contentDiv.innerHTML = `<span class="status-indicator"><em>Initializing Request...</em></span>`;
    msgDiv.appendChild(contentDiv);
    chatBox.appendChild(msgDiv);
    scrollToBottom();
    
    try {
        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text, password: systemPassword })
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error("401");
            }
            throw new Error("Network response was not ok.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let aiText = "";
        let buffer = "";
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            if (value) {
                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split("\n");
                // The last line is either empty or an incomplete chunk, store it until the next flush
                buffer = lines.pop();
                
                for (let line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        
                        if (data.status) {
                            if (data.clear) {
                                contentDiv.innerHTML = ""; // Clear the status indicator text
                            } else {
                                contentDiv.innerHTML = `<span class="status-indicator"><em>${data.status}</em></span>`;
                            }
                        }
                        if (data.chunk) {
                            aiText += data.chunk;
                            // Auto-correct LLM hallucinations where it aggressively truncates the '/images/' directory from the generated HTML SRC path
                            let correctedText = aiText.replace(/https:\/\/(www\.)?site3d\.co\.uk\/help\/(?!images\/)([^"'\)\]>\s]+\.(png|jpg|jpeg|gif))/gi, "https://www.site3d.co.uk/help/images/$2");
                            contentDiv.innerHTML = marked.parse(correctedText);
                        }
                        if (data.error) {
                            contentDiv.innerHTML = `**Error:** ${data.error}`;
                        }
                        scrollToBottom();
                    } catch (e) {
                        console.error("Error parsing JSON line:", line, e);
                    }
                }
            }
        }
    } catch (err) {
        if (err.message.includes("401")) {
            contentDiv.innerHTML = `**Error:** Unauthorized. The password you entered is incorrect or missing.`;
        } else {
            contentDiv.innerHTML = `**Error:** Could not connect to the server. ${err.message}`;
        }
    }
}

sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});

// Implement Event Delegation for generated links to keep chat session alive
chatBox.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') {
        e.preventDefault();
        window.open(e.target.href, '_blank');
    }
});
