from django.shortcuts import render

from django.views.generic import ListView, DetailView, CreateView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .models import Leaderboard, RegistrationForLeaderboard, generate_join_code
from django.shortcuts import redirect, get_object_or_404
from .forms import JoinLeaderboardForm
from django.contrib import messages


class LeaderboardListView(LoginRequiredMixin, ListView):
    model = Leaderboard
    template_name = 'leaderboards/leaderboard_list.html'
    context_object_name = 'leaderboards'

    def get_queryset(self):
        return Leaderboard.objects.filter(
            registrations__competition_registration__user=self.request.user
        ).distinct()


class LeaderboardDetailView(LoginRequiredMixin, DetailView):
    model = Leaderboard
    template_name = 'leaderboards/leaderboard_detail.html'
    context_object_name = 'leaderboard'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        is_member = obj.registrations.filter(
            competition_registration__user=self.request.user
        ).exists()
        
        if not is_member:
            raise PermissionDenied("You do not have permission to view this leaderboard.")
            
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['leaderboard_registrations'] = self.object.registrations.select_related(
            'competition_registration__user'
        ).order_by('-competition_registration__points')
        
        current_user_reg = self.object.registrations.filter(
            competition_registration__user=self.request.user
        ).first()
        
        if current_user_reg and current_user_reg.is_admin:
            context['is_current_user_admin'] = True
        else:
            context['is_current_user_admin'] = False
            
        return context
    
class LeaderboardCreateView(LoginRequiredMixin, CreateView):
    model = Leaderboard
    fields = ['name', 'competition']
    template_name = 'leaderboards/leaderboard_form.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
 
        form.fields['competition'].queryset = form.fields['competition'].queryset.filter(
            registrations__user=self.request.user
        ).distinct()
        return form

    def form_valid(self, form):
        leaderboard = form.save()
        
        competition_registration = self.request.user.competition_registrations.get(
            competition=leaderboard.competition
        )
        
        RegistrationForLeaderboard.objects.create(
            leaderboard=leaderboard,
            competition_registration=competition_registration,
            is_admin=True
        )
        
        return redirect('leaderboard_detail', pk=leaderboard.pk)
    
class LeaderboardJoinView(LoginRequiredMixin, FormView):
    template_name = 'leaderboards/leaderboard_join.html'
    form_class = JoinLeaderboardForm

    def form_valid(self, form):
        
        join_code = form.cleaned_data['join_code'].strip().upper()
        
        try:
            leaderboard = Leaderboard.objects.get(join_code=join_code)
        except Leaderboard.DoesNotExist:
            form.add_error('join_code', 'Invalid invite code. Please try again.')
            return self.form_invalid(form)


        competition_registration, created = self.request.user.competition_registrations.get_or_create(
            competition=leaderboard.competition
        )

        already_member = RegistrationForLeaderboard.objects.filter(
            leaderboard=leaderboard,
            competition_registration=competition_registration
        ).exists()


        if not already_member:
            RegistrationForLeaderboard.objects.create(
                leaderboard=leaderboard,
                competition_registration=competition_registration,
                is_admin=False
            )


        return redirect('leaderboard_detail', pk=leaderboard.pk)
    

class LeaderboardLeaveView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        leaderboard = get_object_or_404(Leaderboard, pk=pk)
        member_reg = get_object_or_404(
            RegistrationForLeaderboard,
            leaderboard=leaderboard,
            competition_registration__user=request.user
        )

        if member_reg.is_admin:
            messages.error(request, "You cannot leave the leaderboard while being an admin. Resign from your role first.")
            return redirect('leaderboard_detail', pk=leaderboard.pk)

        member_reg.delete()
        messages.success(request, f"You have successfully left the leaderboard: {leaderboard.name}.")
        return redirect('leaderboard_list')
    
class LeaderboardManageView(LoginRequiredMixin, DetailView):
    model = Leaderboard
    template_name = 'leaderboards/leaderboard_manage.html'
    context_object_name = 'leaderboard'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
      
        is_admin = obj.registrations.filter(
            competition_registration__user=self.request.user,
            is_admin=True
        ).exists()
            
        if not is_admin:
            raise PermissionDenied("You are not an authorized admin of this leaderboard.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['members'] = self.object.registrations.select_related('competition_registration__user').all()
        
        context['current_admin_reg'] = self.object.registrations.filter(
            competition_registration__user=self.request.user
        ).first()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')

        if action == 'reset_code':
            self.object.join_code = generate_join_code()
            self.object.save()
            messages.success(request, "Invite code has been successfully regenerated!")
            return redirect('leaderboard_manage', pk=self.object.pk)

        elif action == 'delete_leaderboard':
            self.object.delete()
            messages.success(request, "The leaderboard has been permanently deleted.")
            return redirect('leaderboard_list')

        return redirect('leaderboard_manage', pk=self.object.pk)


class LeaderboardMemberActionView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        
        member_reg = get_object_or_404(RegistrationForLeaderboard, pk=pk)
        leaderboard = member_reg.leaderboard

    
        current_user_is_admin = leaderboard.registrations.filter(
            competition_registration__user=request.user,
            is_admin=True
        ).exists()

        if not current_user_is_admin:
            raise PermissionDenied()

        action = request.POST.get('action')

        if action == 'remove_member':
            if member_reg.competition_registration.user == request.user:
                messages.error(request, "You cannot remove yourself. Use the resignation option instead.")
                return redirect('leaderboard_manage', pk=leaderboard.pk)
            
            username = member_reg.competition_registration.user.username
            member_reg.delete()
            messages.success(request, f"Player {username} has been removed from the leaderboard.")

        elif action == 'make_admin':
            member_reg.is_admin = True
            member_reg.save()
            messages.success(request, f"{member_reg.competition_registration.user.username} is now an Admin.")

        elif action == 'resign_admin':
            
            if member_reg.competition_registration.user != request.user:
                raise PermissionDenied()

           
            other_admins_exist = leaderboard.registrations.filter(is_admin=True).exclude(pk=member_reg.pk).exists()
            
            if not other_admins_exist:
                messages.error(request, "You cannot resign because you are the sole admin. Appoint another admin first!")
                return redirect('leaderboard_manage', pk=leaderboard.pk)

            member_reg.is_admin = False
            member_reg.save()
            messages.success(request, "You have stepped down as an administrator.")
            
            return redirect('leaderboard_detail', pk=leaderboard.pk)

        return redirect('leaderboard_manage', pk=leaderboard.pk)