from django import template
import re

register = template.Library()

@register.filter(name='youtube_embed_url')
def youtube_embed_url(url):
    if not url:
        return ''
    
    # Extract video ID from various YouTube URL formats
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',  # Standard watch URL
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^/?]+)',   # Embed URL
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^/?]+)',            # Short URL
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([^/?]+)'    # Live stream URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return f'https://www.youtube.com/embed/{video_id}'
    
    # If no pattern matches, check if the URL is already a video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return f'https://www.youtube.com/embed/{url}'
            
    return url 