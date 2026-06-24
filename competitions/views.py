from django.shortcuts import render

from django.views.generic import ListView, DetailView
from .models import Competition

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