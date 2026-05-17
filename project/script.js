document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatContainer = document.getElementById('chatContainer');
    const messagesContainer = document.getElementById('messages');
    const welcomeScreen = document.getElementById('welcomeScreen');
    const newChatBtn = document.getElementById('newChatBtn');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.querySelector('.sidebar');
    const suggestionCards = document.querySelectorAll('.suggestion-card');

    let isGenerating = false;

    function autoResizeTextarea() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
    }

    function updateSendButton() {
        sendBtn.disabled = messageInput.value.trim() === '' || isGenerating;
    }

    function createMessageElement(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${role}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';

        if (role === 'user') {
            avatarDiv.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>';
        } else {
            avatarDiv.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0902 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2519 24a6.0557 6.0557 0 0 0 5.7717-4.2058 5.9847 5.9847 0 0 0 3.9978-2.9001 6.0557 6.0557 0 0 0-.7395-7.0729zm-10.064 11.4436a3.9653 3.9653 0 0 1-2.8296-1.1093l-.0331-.0331a3.97 3.97 0 0 1-1.153-2.8296c0-.4698.071-.9349.212-1.3807l.0331-.0994a3.9747 3.9747 0 0 1 1.9917-2.3587 3.9606 3.9606 0 0 1 1.7809-.4219c.4698 0 .9349.071 1.3807.212l.0994.0331a3.9747 3.9747 0 0 1 2.3587 1.9917 3.9653 3.9653 0 0 1-.4219 4.6126 3.9747 3.9747 0 0 1-2.3587 1.9917 3.9606 3.9606 0 0 1-1.3807.212l-.0994-.0331a3.9747 3.9747 0 0 1-1.3807-.212z"/></svg>';
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = formatMessage(content);

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);

        return messageDiv;
    }

    function formatMessage(text) {
        let formatted = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code>${code.trim()}</code></pre>`;
        });

        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

        formatted = formatted.replace(/\n/g, '</p><p>');
        formatted = `<p>${formatted}</p>`;

        formatted = formatted.replace(/<p><\/p>/g, '');

        return formatted;
    }

    function simulateResponse(userMessage) {
        const responses = [
            `That's a great question! Let me help you with "${userMessage.substring(0, 50)}${userMessage.length > 50 ? '...' : ''}".\n\nHere's what I think:\n\n**Key Points:**\n- First, consider the context of your question\n- Second, break it down into smaller parts\n- Third, approach it systematically\n\nWould you like me to elaborate on any of these points?`,
            `I'd be happy to help with that! Here's my analysis:\n\nThe topic you mentioned is quite interesting. Let me provide some insights:\n\n1. **Understanding the basics** - It's important to start with foundational concepts\n2. **Practical application** - Theory is best learned through practice\n3. **Advanced techniques** - Once comfortable, explore more complex approaches\n\n\`\`\`python\n# Example code snippet\ndef example():\n    return "Hello, World!"\n\`\`\`\n\nFeel free to ask follow-up questions!`,
            `Great question! Let me break this down for you:\n\n**Overview:**\nThis is a common topic that many people ask about. Here's what you need to know:\n\n- *Point 1*: The first consideration is understanding your goals\n- *Point 2*: Next, evaluate your available resources\n- *Point 3*: Finally, create a step-by-step plan\n\n**Recommendation:**\nStart small and iterate. Don't try to do everything at once.\n\nIs there anything specific you'd like me to clarify?`
        ];

        return responses[Math.floor(Math.random() * responses.length)];
    }

    async function sendMessage(messageText) {
        if (!messageText.trim() || isGenerating) return;

        isGenerating = true;
        updateSendButton();

        if (welcomeScreen.style.display !== 'none') {
            welcomeScreen.style.display = 'none';
            messagesContainer.classList.add('active');
        }

        const userMessage = createMessageElement('user', messageText);
        messagesContainer.appendChild(userMessage);

        messageInput.value = '';
        autoResizeTextarea();
        updateSendButton();

        chatContainer.scrollTop = chatContainer.scrollHeight;

        const loadingMessage = createMessageElement('assistant', 'Thinking...');
        messagesContainer.appendChild(loadingMessage);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1500));

        messagesContainer.removeChild(loadingMessage);

        const response = simulateResponse(messageText);
        const assistantMessage = createMessageElement('assistant', response);
        messagesContainer.appendChild(assistantMessage);

        chatContainer.scrollTop = chatContainer.scrollHeight;

        isGenerating = false;
        updateSendButton();
    }

    messageInput.addEventListener('input', () => {
        autoResizeTextarea();
        updateSendButton();
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(messageInput.value);
        }
    });

    sendBtn.addEventListener('click', () => {
        sendMessage(messageInput.value);
    });

    newChatBtn.addEventListener('click', () => {
        messagesContainer.innerHTML = '';
        messagesContainer.classList.remove('active');
        welcomeScreen.style.display = 'flex';
        messageInput.value = '';
        autoResizeTextarea();
        updateSendButton();
    });

    mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && !sidebar.contains(e.target) && e.target !== mobileMenuBtn) {
            sidebar.classList.remove('open');
        }
    });

    suggestionCards.forEach(card => {
        card.addEventListener('click', () => {
            const text = card.querySelector('.suggestion-text').textContent;
            messageInput.value = text;
            updateSendButton();
            sendMessage(text);
        });
    });

    const conversationItems = document.querySelectorAll('.conversation-item');
    conversationItems.forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.closest('.conversation-menu')) return;

            conversationItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });

    updateSendButton();
    messageInput.focus();
});
