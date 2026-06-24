from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import date

from competitions.models import Competition
from predictions.models import RegistrationForCompetition
from leaderboards.models import Leaderboard, RegistrationForLeaderboard
from leaderboards.services import (
    join_leaderboard,
    resign_from_admin,
    remove_member,
)

User = get_user_model()

class LeaderboardServicesTests(TestCase):
    def setUp(self):
        # Create Users
        self.admin_user = User.objects.create_user(username='admin_dude', password='123')
        self.regular_user = User.objects.create_user(username='regular_dude', password='123')
        self.outsider = User.objects.create_user(username='outsider', password='123')

        # Create Competition
        self.competition = Competition.objects.create(
            api_id=999, season_api_id=2024, name="Champions League", code="CL",
            date_start=date(2024, 9, 1), date_finish=date(2025, 6, 1), emblem="url"
        )
        
        # Register admin to competition
        self.admin_comp_reg = RegistrationForCompetition.objects.create(
            user=self.admin_user, competition=self.competition
        )

        # Create Leaderboard and assign admin
        self.leaderboard = Leaderboard.objects.create(
            name="Office League", competition=self.competition, join_code="SECRET123"
        )
        self.admin_board_reg = RegistrationForLeaderboard.objects.create(
            leaderboard=self.leaderboard,
            competition_registration=self.admin_comp_reg,
            is_admin=True
        )

        # Add a regular member
        self.reg_comp_reg = RegistrationForCompetition.objects.create(
            user=self.regular_user, competition=self.competition
        )
        self.regular_board_reg = RegistrationForLeaderboard.objects.create(
            leaderboard=self.leaderboard,
            competition_registration=self.reg_comp_reg,
            is_admin=False
        )


    def test_join_leaderboard_success(self):
        """User successfully joins with a valid code and gets auto-registered for the competition."""
        board = join_leaderboard(self.outsider, "SECRET123")
        
        self.assertEqual(board, self.leaderboard)
        
        # Verify competition registration was created automatically
        comp_reg_exists = RegistrationForCompetition.objects.filter(
            user=self.outsider, competition=self.competition
        ).exists()
        self.assertTrue(comp_reg_exists)
        
        # Verify leaderboard registration was created
        board_reg = RegistrationForLeaderboard.objects.get(
            competition_registration__user=self.outsider, leaderboard=self.leaderboard
        )
        self.assertFalse(board_reg.is_admin)

    def test_join_leaderboard_invalid_code(self):
        """Joining with a bad code raises a ValidationError."""
        with self.assertRaisesMessage(ValidationError, "Invalid invite code. Please try again."):
            join_leaderboard(self.outsider, "BADCODE")

    # --- RESIGNATION TESTS ---

    def test_resign_from_admin_fails_if_sole_admin(self):
        """An admin cannot resign if no other admins exist."""
        with self.assertRaisesMessage(ValidationError, "You cannot resign because you are the sole admin."):
            resign_from_admin(actor=self.admin_user, target_reg_id=self.admin_board_reg.id)
            
        # Verify they are still an admin
        self.admin_board_reg.refresh_from_db()
        self.assertTrue(self.admin_board_reg.is_admin)

    def test_resign_from_admin_success_with_multiple_admins(self):
        """An admin can resign if there is at least one other admin."""
        # Promote the regular user to admin first
        self.regular_board_reg.is_admin = True
        self.regular_board_reg.save()

        resign_from_admin(actor=self.admin_user, target_reg_id=self.admin_board_reg.id)
        
        self.admin_board_reg.refresh_from_db()
        self.assertFalse(self.admin_board_reg.is_admin)

    # --- KICKING MEMBERS TESTS ---

    def test_remove_member_success(self):
        """An admin can successfully remove a regular member."""
        removed_username = remove_member(actor=self.admin_user, target_reg_id=self.regular_board_reg.id)
        
        self.assertEqual(removed_username, 'regular_dude')
        self.assertFalse(
            RegistrationForLeaderboard.objects.filter(id=self.regular_board_reg.id).exists()
        )

    def test_remove_member_fails_if_actor_not_admin(self):
        """A regular user cannot kick anyone and gets PermissionDenied."""
        with self.assertRaisesMessage(PermissionDenied, "You are not an admin of this leaderboard."):
            remove_member(actor=self.regular_user, target_reg_id=self.admin_board_reg.id)

    def test_remove_member_fails_when_kicking_self(self):
        """An admin cannot kick themselves."""
        with self.assertRaisesMessage(ValidationError, "You cannot remove yourself."):
            remove_member(actor=self.admin_user, target_reg_id=self.admin_board_reg.id)