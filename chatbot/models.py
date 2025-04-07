from django.db import models
from django.conf import settings

# Create your models here.

class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(db_collation='utf8mb4_unicode_ci')
    response = models.TextField(db_collation='utf8mb4_unicode_ci')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"
