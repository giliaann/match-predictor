from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Leaderboard, RegistrationForLeaderboard, generate_join_code

@transaction.atomic
def create_leaderboard(user, name, competition):
    """
    Creates a new leaderboard and automatically assigns the creator as its admin.
    """
    leaderboard = Leaderboard.objects.create(name=name, competition=competition)
    
    competition_registration = user.competition_registrations.get(competition=competition)
    
    RegistrationForLeaderboard.objects.create(
        leaderboard=leaderboard,
        competition_registration=competition_registration,
        is_admin=True
    )
    return leaderboard

@transaction.atomic
def join_leaderboard(user, join_code):
    """
    Adds a user to a leaderboard using an invite code.
    Validates the code and ensures the user isn't already a member.
    """
    join_code = join_code.strip().upper()
    
    try:
        leaderboard = Leaderboard.objects.get(join_code=join_code)
    except Leaderboard.DoesNotExist:
        raise ValidationError("Invalid invite code. Please try again.")

    competition_registration, _ = user.competition_registrations.get_or_create(
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
        
    return leaderboard

def leave_leaderboard(user, leaderboard_id):
    """
    Removes a user from a leaderboard. Blocks admins from leaving directly.
    """
    leaderboard = get_object_or_404(Leaderboard, pk=leaderboard_id)
    member_reg = get_object_or_404(
        RegistrationForLeaderboard,
        leaderboard=leaderboard,
        competition_registration__user=user
    )

    if member_reg.is_admin:
        raise ValidationError("You cannot leave the leaderboard while being an admin. Resign from your role first.")

    member_reg.delete()
    return leaderboard

def reset_leaderboard_code(leaderboard):
    """
    Generates and saves a new join code for the leaderboard.
    """
    leaderboard.join_code = generate_join_code()
    leaderboard.save(update_fields=['join_code'])
    return leaderboard

def delete_leaderboard(leaderboard):
    """
    Permanently deletes the leaderboard.
    """
    leaderboard.delete()


def _get_target_registration(actor, target_reg_id):
    """
    Internal helper function to validate if the actor has admin rights 
    over the target registration's leaderboard.
    """
    target_reg = get_object_or_404(RegistrationForLeaderboard, pk=target_reg_id)
    leaderboard = target_reg.leaderboard
    
    actor_is_admin = leaderboard.registrations.filter(
        competition_registration__user=actor,
        is_admin=True
    ).exists()
    
    if not actor_is_admin:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You are not an admin of this leaderboard.")
        
    return target_reg, leaderboard

def remove_member(actor, target_reg_id):
    """
    Removes a target member from the leaderboard. Prevents kicking admins or self.
    """
    target_reg, _ = _get_target_registration(actor, target_reg_id)
    
    if target_reg.competition_registration.user == actor:
        raise ValidationError("You cannot remove yourself. Use the resignation option instead.")
    
    if target_reg.is_admin:
        raise ValidationError("You cannot kick another administrator. They must resign from their role first.")
    
    username = target_reg.competition_registration.user.username
    target_reg.delete()
    return username

def promote_to_admin(actor, target_reg_id):
    """
    Grants admin privileges to a target member.
    """
    target_reg, _ = _get_target_registration(actor, target_reg_id)
    target_reg.is_admin = True
    target_reg.save(update_fields=['is_admin'])
    return target_reg.competition_registration.user.username

def resign_from_admin(actor, target_reg_id):
    """
    Allows an admin to step down, preventing action if they are the only admin left.
    """
    target_reg, leaderboard = _get_target_registration(actor, target_reg_id)
    
    if target_reg.competition_registration.user != actor:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You can only resign from your own admin status.")
    
    other_admins_exist = leaderboard.registrations.filter(is_admin=True).exclude(pk=target_reg.pk).exists()
    
    if not other_admins_exist:
        raise ValidationError("You cannot resign because you are the sole admin. Appoint another admin first!")

    target_reg.is_admin = False
    target_reg.save(update_fields=['is_admin'])
    return leaderboard