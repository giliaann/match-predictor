from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from .models import Competition
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

class CompetitionListView(ListView):
    model = Competition
    template_name = 'competitions/competition_list.html'
    context_object_name = 'competitions'
    
    def get_queryset(self):
        return Competition.objects.all().order_by('-date_start')
    
class CompetitionDetailView(DetailView):
    model = Competition
    template_name = 'competitions/competition_detail.html'
    context_object_name = 'competition'
    slug_field = 'code'
    slug_url_kwarg = 'code'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        competition = self.object

        all_stages = competition.matches.values_list('stage', flat=True).distinct().order_by('stage')
        context['all_stages'] = all_stages

        current_stage = self.request.GET.get('stage') or (all_stages[0] if all_stages else None)
        context['current_stage'] = current_stage

        all_groups = []
        current_group = None
        if current_stage:
            all_groups = competition.matches.filter(stage=current_stage).values_list('group', flat=True).distinct().order_by('group')
            all_groups = [g for g in all_groups if g]  # odsiewamy None/puste
            current_group = self.request.GET.get('group') or (all_groups[0] if all_groups else None)
        
        context['all_groups'] = all_groups
        context['current_group'] = current_group

        match_filter = {'competition': competition, 'stage': current_stage}
        if current_group:
            match_filter['group'] = current_group

        matches = competition.matches.filter(**match_filter).select_related('home_team', 'away_team').order_by('kickoff_time')

        is_registered = False
        user_predictions = {}

        if user.is_authenticated:
            registration = competition.registrations.filter(user=user).first()
            if registration:
                is_registered = True
                predictions = registration.predictions.all()
                user_predictions = {pred.match_id: pred for pred in predictions}
                
        context['is_registered'] = is_registered

        for match in matches:
            match.user_prediction = user_predictions.get(match.id)

        context['matches'] = matches
        return context

class CompetitionLeaveView(LoginRequiredMixin, View):
    def post(self, request, code, *args, **kwargs):
        competition = get_object_or_404(Competition, code=code)
        
        competition_registration = get_object_or_404(
            request.user.competition_registrations,
            competition=competition
        )
        
        is_admin_somewhere = competition_registration.leaderboards.filter(
            is_admin=True
        ).exists()
        
        if is_admin_somewhere:
            messages.error(
                request, 
                "You cannot leave this competition because you are an administrator of a private leaderboard within it. "
                "Step down from your admin position or delete the leaderboard first."
            )
            return redirect('competition_detail', code=competition.code)
            
        competition_registration.delete()
        messages.success(request, f"You have successfully left the competition: {competition.name}.")
        return redirect('competition_list')