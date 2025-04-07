function startStream(eventId) {
    fetch(`/events/${eventId}/start-stream/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Failed to start stream: ' + data.message);
        }
    });
}

function stopStream(eventId) {
    fetch(`/events/${eventId}/stop-stream/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Failed to stop stream: ' + data.message);
        }
    });
}

// Check stream status every 30 seconds
function checkStreamStatus(eventId) {
    setInterval(() => {
        fetch(`/events/${eventId}/stream-status/`)
        .then(response => response.json())
        .then(data => {
            if (data.is_streaming) {
                document.getElementById('streamPlayer').style.display = 'block';
                document.querySelector('.stream-waiting').style.display = 'none';
            } else {
                document.getElementById('streamPlayer').style.display = 'none';
                document.querySelector('.stream-waiting').style.display = 'block';
            }
        });
    }, 30000);
}

function startYouTubeStream(eventId) {
    const youtubeUrl = document.getElementById('youtube_url').value;
    if (!youtubeUrl) {
        alert('Please enter a YouTube stream URL');
        return;
    }

    fetch(`/events/${eventId}/start-stream/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            youtube_url: youtubeUrl
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Failed to start stream: ' + data.message);
        }
    });
} 