from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Leaderboard
from .forms import JoinLeaderboardForm
from . import selectors
from . import services


class LeaderboardListView(LoginRequiredMixin, ListView):
    template_name = 'leaderboards/leaderboard_list.html'
    context_object_name = 'leaderboards'

    def get_queryset(self):
        return selectors.get_user_leaderboards(self.request.user)


class LeaderboardDetailView(LoginRequiredMixin, DetailView):
    template_name = 'leaderboards/leaderboard_detail.html'
    context_object_name = 'leaderboard'

    def get_object(self, queryset=None):
        return selectors.get_leaderboard_for_member(self.kwargs.get('pk'), self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        leaderboard = self.object
        
        user_reg = selectors.get_user_registration_for_leaderboard(leaderboard, self.request.user)
        context['leaderboard_registrations'] = selectors.get_leaderboard_registrations(leaderboard)
        context['is_current_user_admin'] = user_reg.is_admin if user_reg else False
        
        return context


class LeaderboardCreateView(LoginRequiredMixin, CreateView):
    model = Leaderboard
    fields = ['name', 'competition']
    template_name = 'leaderboards/leaderboard_form.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['competition'].queryset = selectors.get_user_competitions_for_form(self.request.user)
        return form

    def form_valid(self, form):
        leaderboard = services.create_leaderboard(
            user=self.request.user,
            name=form.cleaned_data['name'],
            competition=form.cleaned_data['competition']
        )
        return redirect('leaderboard_detail', pk=leaderboard.pk)


class LeaderboardJoinView(LoginRequiredMixin, FormView):
    template_name = 'leaderboards/leaderboard_join.html'
    form_class = JoinLeaderboardForm

    def form_valid(self, form):
        try:
    
            leaderboard = services.join_leaderboard(
                user=self.request.user,
                join_code=form.cleaned_data['join_code']
            )
            return redirect('leaderboard_detail', pk=leaderboard.pk)
        except ValidationError as e:
            
            form.add_error('join_code', e.message)
            return self.form_invalid(form)


class LeaderboardLeaveView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            leaderboard = services.leave_leaderboard(user=request.user, leaderboard_id=pk)
            messages.success(request, f"You have successfully left the leaderboard: {leaderboard.name}.")
            return redirect('leaderboard_list')
        except ValidationError as e:
    
            messages.error(request, e.message)
            return redirect('leaderboard_detail', pk=pk)


class LeaderboardManageView(LoginRequiredMixin, DetailView):
    template_name = 'leaderboards/leaderboard_manage.html'
    context_object_name = 'leaderboard'

    def get_object(self, queryset=None):
   
        return selectors.get_leaderboard_for_admin(self.kwargs.get('pk'), self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['members'] = self.object.registrations.select_related('competition_registration__user').all()
        context['current_admin_reg'] = selectors.get_user_registration_for_leaderboard(self.object, self.request.user)
        return context

    def post(self, request, pk, *args, **kwargs):
        leaderboard = self.get_object()
        action = request.POST.get('action')

        if action == 'reset_code':
            services.reset_leaderboard_code(leaderboard)
            messages.success(request, "Invite code has been successfully regenerated!")
            return redirect('leaderboard_manage', pk=leaderboard.pk)

        elif action == 'delete_leaderboard':
            services.delete_leaderboard(leaderboard)
            messages.success(request, "The leaderboard has been permanently deleted.")
            return redirect('leaderboard_list')

        return redirect('leaderboard_manage', pk=leaderboard.pk)


class LeaderboardMemberActionView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
      
        action = request.POST.get('action')

        try:
            if action == 'remove_member':
                username = services.remove_member(actor=request.user, target_reg_id=pk)
                messages.success(request, f"Player {username} has been removed from the leaderboard.")
                
            elif action == 'make_admin':
                username = services.promote_to_admin(actor=request.user, target_reg_id=pk)
                messages.success(request, f"{username} is now an Admin.")
                
            elif action == 'resign_admin':
                leaderboard = services.resign_from_admin(actor=request.user, target_reg_id=pk)
                messages.success(request, "You have stepped down as an administrator.")
                return redirect('leaderboard_detail', pk=leaderboard.pk)
                
        except ValidationError as e:
            
            messages.error(request, e.message)
            
        referer_url = request.META.get('HTTP_REFERER')
        if referer_url:
            return redirect(referer_url)
            
        return redirect('leaderboard_list')