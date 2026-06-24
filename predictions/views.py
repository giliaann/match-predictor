from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from competitions.models import Competition
from .models import RegistrationForCompetition

class JoinCompetitionView(LoginRequiredMixin, View):
    """
    View handling user registration for a competition.
    It accepts POST requests only and redirects back to the competition detail page.
    """
    
    def post(self, request, code):
        competition = get_object_or_404(Competition, code=code)
        
        RegistrationForCompetition.objects.get_or_create(
            user=request.user,
            competition=competition
        )
        
        return redirect('competition_detail', code=competition.code)