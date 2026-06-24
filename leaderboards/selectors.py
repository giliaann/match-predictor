from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Leaderboard, RegistrationForLeaderboard
from competitions.models import Competition

def get_user_leaderboards(user):
    """
    Returns all leaderboards to which the given user belongs.
    """
    return Leaderboard.objects.filter(
        registrations__competition_registration__user=user
    ).distinct()

def get_leaderboard_for_member(leaderboard_id, user):
    """
    Returns the leaderboard, ensuring the user is a registered member.
    Raises PermissionDenied if the user is not a member.
    """
    leaderboard = get_object_or_404(Leaderboard, pk=leaderboard_id)
    is_member = leaderboard.registrations.filter(
        competition_registration__user=user
    ).exists()
    
    if not is_member:
        raise PermissionDenied("You do not have permission to view this leaderboard.")
    
    return leaderboard

def get_leaderboard_for_admin(leaderboard_id, user):
    """
    Returns the leaderboard, ensuring the user is an admin.
    Raises PermissionDenied if the user lacks admin privileges.
    """
    leaderboard = get_object_or_404(Leaderboard, pk=leaderboard_id)
    is_admin = leaderboard.registrations.filter(
        competition_registration__user=user,
        is_admin=True
    ).exists()
    
    if not is_admin:
        raise PermissionDenied("You are not an authorized admin of this leaderboard.")
    
    return leaderboard

def get_leaderboard_registrations(leaderboard):
    """
    Fetches all registrations for a given leaderboard, ordered by points descending.
    """
    return leaderboard.registrations.select_related(
        'competition_registration__user'
    ).order_by('-competition_registration__points')

def get_user_registration_for_leaderboard(leaderboard, user):
    """
    Returns the specific RegistrationForLeaderboard object for a user.
    """
    return leaderboard.registrations.filter(
        competition_registration__user=user
    ).first()

def get_user_competitions_for_form(user):
    """
    Returns a queryset of competitions the user is registered in, 
    used to populate the dropdown in the creation form.
    """
    return Competition.objects.filter(registrations__user=user).distinct()