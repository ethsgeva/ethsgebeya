from django.contrib import messages
from django.shortcuts import render

def already_authenticated_message(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already signed in and have an account.')
        return None  # Only set the message, do not render a new page
    return None
