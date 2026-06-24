from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from .models import Competition
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from . import selectors, services
from django.core.exceptions import ValidationError

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
        
        details_data = selectors.get_competition_details_data(
            competition=self.object,
            user=self.request.user,
            request_stage=self.request.GET.get('stage'),
            request_group=self.request.GET.get('group')
        )
        
        context.update(details_data)
        return context

class CompetitionLeaveView(LoginRequiredMixin, View):
    def post(self, request, code, *args, **kwargs):
        competition = get_object_or_404(Competition, code=code)
        
        try:
            services.leave_competition(user=request.user, competition=competition)
            messages.success(request, f"You have successfully left the competition: {competition.name}.")
        except ValidationError as e:
            
            messages.error(request, e.message)
            return redirect('competition_detail', code=competition.code)
            
        return redirect('competition_list')