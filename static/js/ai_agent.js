document.addEventListener('DOMContentLoaded', function() {
    const testAgentBtn = document.getElementById('test-agent-btn');
    const testAgentSection = document.getElementById('test-agent-section');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatContainer = document.getElementById('chat-container');
    
    // Generate a unique session key for this chat session
    const sessionKey = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    
    // Initialize UI
    if (testAgentSection) {
        testAgentSection.style.display = 'none';
    }
    
    // Show/hide test section
    testAgentBtn.addEventListener('click', function() {
        testAgentSection.style.display = testAgentSection.style.display === 'none' ? 'block' : 'none';
        if (testAgentSection.style.display === 'block') {
            messageInput.focus();
        }
    });
    
    // Add a message to the chat
    function addMessage(text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
        
        // Create message content
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = text.replace(/\n/g, '<br>');
        
        // Create timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const now = new Date();
        timeDiv.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Add content and time to message
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        
        // Add message to chat
        chatContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Add loading indicator
    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'loading-dot';
            loadingDiv.appendChild(dot);
        }
        
        chatContainer.appendChild(loadingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return loadingDiv;
    }
    
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, true);
        
        // Clear input
        messageInput.value = '';
        
        // Show loading indicator
        const loadingIndicator = addLoadingIndicator();
        
        // Get the CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Disable input and send button during processing
        messageInput.disabled = true;
        sendButton.disabled = true;
        
        // Send message to API
        fetch(processMessageUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                business_id: businessId,
                message: message,
                session_key: sessionKey
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicator
            chatContainer.removeChild(loadingIndicator);
            
            // Re-enable input and send button
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
            
            if (data.success) {
                // Add assistant response to chat
                addMessage(data.response, false);
            } else {
                // Show error
                const errorDiv = document.createElement('div');
                errorDiv.className = 'system-message text-center text-danger mb-3';
                errorDiv.textContent = 'Error: ' + (data.error || 'Unknown error occurred');
                chatContainer.appendChild(errorDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        })
        .catch(error => {
            // Remove loading indicator
            chatContainer.removeChild(loadingIndicator);
            
            // Re-enable input and send button
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
            
            // Show error
            const errorDiv = document.createElement('div');
            errorDiv.className = 'system-message text-center text-danger mb-3';
            errorDiv.textContent = 'Network error: Could not connect to the server';
            chatContainer.appendChild(errorDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            console.error('Error:', error);
        });
    }
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
