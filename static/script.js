document.addEventListener("DOMContentLoaded", function () {
    var sendButton = document.getElementById("send-button");
    var chatMessages = document.getElementById("chat-messages");
    var chatInput = document.getElementById("chat-input");

    fetchGreetingMessage(); // Selamlama mesajını çek

    function fetchGreetingMessage() {
        fetch('/get_greeting')
            .then(response => response.json())
            .then(data => {
                if (data.greeting) {
                    displayGreeting(data.greeting);
                }
            })
            .catch(error => console.error('Error fetching greeting:', error));
    }

    function displayGreeting(greeting) {
        var greetingMessage = '<div class="bot-response">Bot: ' + greeting + '</div>';
        chatMessages.innerHTML += greetingMessage;
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
    }

    // Form submit eventini dinle
    var form = document.querySelector('form');
    form.addEventListener('submit', function(event) {
        event.preventDefault(); // Formun normal submit işlemini engelle
        sendData();
    });

    function sendData(){
        var userInput = chatInput.value;
        if(!userInput.trim()) {
            console.error('Input is empty.');
            return; // Kullanıcı girdisi boş ise gönderim yapma
        }
        // AJAX request to send data
        fetch('/handle_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ "chat-input": userInput })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(response => {
            displayResponse(userInput, response);
        })
        .catch(error => {
            console.error('Error:', error);
            displayError('Unable to process your request at this time.');
        });
    }

    function displayResponse(userInput, response) {
        var userMessage = '<div class="user-message">You: ' + userInput + '</div>';
        var botResponse = '<div class="bot-response">Bot: ';

        if(response.error) {
            botResponse += 'Error ' + response.error;
        } else {
            if(response.response) {
                botResponse += response.response;
            } else {
                botResponse += 'Sorry, I could not retrieve the weather information.';
            }
        }
        
        botResponse += '</div>';
        chatMessages.innerHTML += userMessage + botResponse;
        chatInput.value = ''; // Clear input field
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom                
    }

    function displayError(message) {
        var errorMessage = '<div class="error-message">Error: ' + message + '</div>';
        chatMessages.innerHTML += errorMessage;
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
    }

});
