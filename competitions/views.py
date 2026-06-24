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
    
        if user.is_authenticated:
            context['is_registered'] = self.object.registrations.filter(user=user).exists()
        else:
            context['is_registered'] = False
            
        context['matches'] = self.object.matches.all().order_by('kickoff_time')
        
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