from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from competitions.models import Competition, Match
from .models import RegistrationForCompetition
from django.http import HttpResponse
from . import services
from django.core.exceptions import ValidationError

class JoinCompetitionView(LoginRequiredMixin, View):
    """
    View handling user registration for a competition.
    """
    def post(self, request, code):
        competition = get_object_or_404(Competition, code=code)
        services.join_competition(user=request.user, competition=competition)
        return redirect('competition_detail', code=competition.code)

class PredictMatchHTMXView(LoginRequiredMixin, View):
    """
    Handles mass updates of match predictions via HTMX.
    """
    def post(self, request, code, *args, **kwargs):
        competition = get_object_or_404(Competition, code=code)
        registration = competition.registrations.filter(user=request.user).first()
        
        if not registration:
            return HttpResponse('<span style="color: #dc3545;">You have to be registered for a selected competition.</span>')

        match_ids = request.POST.getlist('match_id')
        home_scores = request.POST.getlist('home_score')
        away_scores = request.POST.getlist('away_score')

        try:
            stats = services.process_match_predictions(
                registration=registration,
                competition=competition,
                match_ids=match_ids,
                home_scores=home_scores,
                away_scores=away_scores
            )
        except ValidationError:
            return HttpResponse('<span style="color: #dc3545;">Invalid form.</span>')

        if stats['saved'] > 0 or stats['deleted'] > 0 or stats['incomplete'] > 0:
            msg_parts = []
            if stats['saved'] > 0:
                msg_parts.append(f"Saved: {stats['saved']}")
            if stats['deleted'] > 0:
                msg_parts.append(f"Deleted: {stats['deleted']}")
            if stats['incomplete'] > 0:
                msg_parts.append(f"Omitted incomplete: {stats['incomplete']}")
            
            final_msg = " | ".join(msg_parts)
            return HttpResponse(f'<span style="color: #10b981;">{final_msg}</span>')
            
        return HttpResponse('<span style="color: #64748b;">No changes made</span>')