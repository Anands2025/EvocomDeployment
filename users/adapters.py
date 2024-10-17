from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin is None:
            return redirect(reverse('users:login'))  # Adjust 'users:login' to your actual login URL name
        return super().pre_social_login(request, sociallogin)