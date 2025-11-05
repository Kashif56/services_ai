// AI Website Chat Builder JavaScript
// ChatGPT-style conversational interface

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const userPrompt = document.getElementById('userPrompt');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    
    let currentSessionId = null;
    let pollInterval = null;
    let currentAIMessageElement = null;
    
    // Auto-resize textarea
    userPrompt.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Handle Enter key (submit) vs Shift+Enter (new line)
    userPrompt.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
    
    // Handle suggestion buttons
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const suggestion = this.getAttribute('data-suggestion');
            userPrompt.value = suggestion;
            userPrompt.focus();
            // Auto-resize
            userPrompt.style.height = 'auto';
            userPrompt.style.height = (userPrompt.scrollHeight) + 'px';
        });
    });
    
    // Handle form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const prompt = userPrompt.value.trim();
        if (!prompt) return;
        
        // Disable input
        userPrompt.disabled = true;
        sendBtn.disabled = true;
        
        // Add user message to chat
        addUserMessage(prompt);
        
        // Clear input
        userPrompt.value = '';
        userPrompt.style.height = 'auto';
        
        // Add AI message with generating status
        addAIMessageWithStatus('🚀 Starting website generation...');
        
        try {
            // Start generation
            const response = await fetch('/ai-website/api/generate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    business_name: businessName,
                    prompt: prompt
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                currentSessionId = data.session_id;
                
                // Start processing
                await processGeneration(currentSessionId);
                
                // Start polling for progress
                startProgressPolling(currentSessionId);
            } else {
                updateAIMessageStatus('❌ Error: ' + (data.error || 'Failed to start generation'), 'failed');
                enableInput();
            }
        } catch (error) {
            updateAIMessageStatus('❌ Network error: ' + error.message, 'failed');
            enableInput();
        }
    });
    
    // Add user message to chat
    function addUserMessage(text) {
        const messageHtml = `
            <div class="message user-message">
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-time">Just now</span>
                        <span class="message-author">You</span>
                    </div>
                    <div class="message-text">
                        ${escapeHtml(text)}
                    </div>
                </div>
                <div class="message-avatar">
                    <i class="fas fa-user"></i>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', messageHtml);
        scrollToBottom();
    }
    
    // Add AI message with generating status
    function addAIMessageWithStatus(text) {
        const messageHtml = `
            <div class="message ai-message" id="currentAIMessage">
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-author">AI Assistant</span>
                        <span class="message-time">Just now</span>
                        <span class="badge badge-warning">
                            <i class="fas fa-spinner fa-spin"></i> Processing
                        </span>
                    </div>
                    <div class="message-text">
                        <div class="generating-text">${text}</div>
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', messageHtml);
        currentAIMessageElement = document.getElementById('currentAIMessage');
        scrollToBottom();
    }
    
    // Update AI message status
    function updateAIMessageStatus(text, status = 'processing') {
        if (!currentAIMessageElement) return;
        
        const messageText = currentAIMessageElement.querySelector('.message-text');
        const badge = currentAIMessageElement.querySelector('.badge');
        
        if (status === 'completed') {
            badge.className = 'badge badge-success';
            badge.innerHTML = '<i class="fas fa-check-circle"></i> Completed';
            messageText.innerHTML = `
                <p>${text}</p>
                <div class="message-actions">
                    <button class="preview-btn" onclick="scrollToPreview()">
                        <i class="fas fa-eye"></i> View in Preview
                    </button>
                </div>
            `;
        } else if (status === 'failed') {
            badge.className = 'badge badge-danger';
            badge.innerHTML = '<i class="fas fa-times-circle"></i> Failed';
            messageText.innerHTML = `<p>${text}</p>`;
        } else {
            messageText.innerHTML = `<div class="generating-text">${text}</div>`;
        }
        
        scrollToBottom();
    }
    
    
    // Process generation
    async function processGeneration(sessionId) {
        try {
            const response = await fetch(`/ai-website/api/process/${sessionId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            // Processing happens in background, polling will track progress
        } catch (error) {
            console.error('Error starting processing:', error);
        }
    }
    
    // Start polling for progress
    function startProgressPolling(sessionId) {
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/ai-website/api/status/${sessionId}/`);
                const data = await response.json();
                
                if (data.success) {
                    // Update the message with progress
                    if (data.message) {
                        updateAIMessageStatus(data.message, 'processing');
                    }
                    
                    if (data.completed) {
                        stopProgressPolling();
                        
                        if (data.status === 'completed') {
                            // Success
                            updateAIMessageStatus(
                                '✅ Website generated successfully! Your website is ready to view.',
                                'completed'
                            );
                            enableInput();
                            
                            // Trigger preview refresh
                            window.dispatchEvent(new Event('websiteGenerated'));
                            
                            // Reload page after a short delay to show updated preview
                            setTimeout(() => {
                                window.location.reload();
                            }, 2000);
                        } else if (data.status === 'failed') {
                            // Failed
                            updateAIMessageStatus(
                                data.error || 'Generation failed. Please try again.',
                                'failed'
                            );
                            enableInput();
                        }
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
                stopProgressPolling();
                updateAIMessageStatus('❌ Lost connection to server. Please try again.', 'failed');
                enableInput();
            }
        }, 1000); // Poll every second
    }
    
    // Stop polling
    function stopProgressPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }
    
    // Enable input
    function enableInput() {
        userPrompt.disabled = false;
        sendBtn.disabled = false;
        userPrompt.focus();
    }
    
    // Scroll to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/\n/g, '<br>');
    }
    
    // Get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Initial scroll to bottom
    scrollToBottom();
    
    // Focus on input
    userPrompt.focus();
});
