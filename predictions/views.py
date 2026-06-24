from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from competitions.models import Competition, Match
from .models import RegistrationForCompetition
from django.http import HttpResponse

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
    

class PredictMatchHTMXView(LoginRequiredMixin, View):
    def post(self, request, code, *args, **kwargs):
        competition = get_object_or_404(Competition, code=code)
        registration = competition.registrations.filter(user=request.user).first()
        
        if not registration:
            return HttpResponse('<span style="color: #dc3545;">You have to be registered for a selected competition.</span>')


        match_ids = request.POST.getlist('match_id')
        home_scores = request.POST.getlist('home_score')
        away_scores = request.POST.getlist('away_score')

                
        if not (len(match_ids) == len(home_scores) == len(away_scores)):
            return HttpResponse('<span style="color: #dc3545;">Invalid form.</span>')

        saved_count = 0
        deleted_count = 0
        incomplete_count = 0

        for i in range(len(match_ids)):
            m_id = match_ids[i]
            h_score = home_scores[i]
            a_score = away_scores[i]

            try:
                match = Match.objects.get(id=m_id, competition=competition)

                if match.has_started:
                    continue
                
                if h_score != '' and a_score != '':
                    registration.predictions.update_or_create(
                        match=match,
                        defaults={
                            'home_score_prediction': int(h_score),
                            'away_score_prediction': int(a_score)
                        }
                    )
                    saved_count += 1
                    
                elif h_score == '' and a_score == '':
                    deleted, _ = registration.predictions.filter(match=match).delete()
                    if deleted > 0:
                        deleted_count += 1

                else:
                    incomplete_count+=1

            except (Match.DoesNotExist, ValueError):
                continue

        if saved_count > 0 or deleted_count > 0 or incomplete_count > 0:
            msg_parts = []
            if saved_count > 0:
                msg_parts.append(f"Saved: {saved_count}")
            if deleted_count > 0:
                msg_parts.append(f"Deleted: {deleted_count}")
            if incomplete_count > 0:
                msg_parts.append(f"Ommited incomplete: {incomplete_count}")
            
            final_msg = " | ".join(msg_parts)
            return HttpResponse(f'<span style="color: #10b981;">{final_msg}</span>')
        else:
            return HttpResponse('<span style="color: #64748b;">No changes made</span>')