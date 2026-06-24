from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from datetime import date

from competitions.models import Competition
from predictions.models import RegistrationForCompetition
from leaderboards.models import Leaderboard, RegistrationForLeaderboard
from leaderboards.selectors import (
    get_leaderboard_for_member,
    get_leaderboard_for_admin
)

User = get_user_model()

class LeaderboardSecuritySelectorsTests(TestCase):
    def setUp(self):
        # Create Users
        self.admin_user = User.objects.create_user(username='admin_boss', password='123')
        self.regular_member = User.objects.create_user(username='regular_joe', password='123')
        self.random_stranger = User.objects.create_user(username='stranger', password='123')

        # Create Competition and Registrations
        self.competition = Competition.objects.create(
            api_id=999, season_api_id=2024, name="Champions League", code="CL",
            date_start=date(2024, 9, 1), date_finish=date(2025, 6, 1), emblem="url"
        )
        
        self.admin_comp_reg = RegistrationForCompetition.objects.create(
            user=self.admin_user, competition=self.competition
        )
        self.member_comp_reg = RegistrationForCompetition.objects.create(
            user=self.regular_member, competition=self.competition
        )

        # Create Leaderboard
        self.leaderboard = Leaderboard.objects.create(
            name="Office League", competition=self.competition, join_code="SEC123"
        )

        # Assign Roles in the Leaderboard
        RegistrationForLeaderboard.objects.create(
            leaderboard=self.leaderboard,
            competition_registration=self.admin_comp_reg,
            is_admin=True
        )
        RegistrationForLeaderboard.objects.create(
            leaderboard=self.leaderboard,
            competition_registration=self.member_comp_reg,
            is_admin=False
        )

    # --- GET LEADERBOARD FOR MEMBER TESTS ---

    def test_get_leaderboard_for_member_success(self):
        """A registered member should be able to retrieve the leaderboard."""
        board = get_leaderboard_for_member(self.leaderboard.id, self.regular_member)
        self.assertEqual(board, self.leaderboard)

    def test_get_leaderboard_for_member_denied_for_stranger(self):
        """A user who is not registered to the leaderboard should be blocked."""
        with self.assertRaisesMessage(PermissionDenied, "You do not have permission to view this leaderboard."):
            get_leaderboard_for_member(self.leaderboard.id, self.random_stranger)

    def test_get_leaderboard_for_member_404(self):
        """Requesting a non-existent leaderboard should raise a 404 error."""
        with self.assertRaises(Http404):
            get_leaderboard_for_member(9999, self.regular_member)

    # --- GET LEADERBOARD FOR ADMIN TESTS ---

    def test_get_leaderboard_for_admin_success(self):
        """An admin should successfully retrieve the leaderboard."""
        board = get_leaderboard_for_admin(self.leaderboard.id, self.admin_user)
        self.assertEqual(board, self.leaderboard)

    def test_get_leaderboard_for_admin_denied_for_regular_member(self):
        """A regular member without admin rights should be blocked from admin access."""
        with self.assertRaisesMessage(PermissionDenied, "You are not an authorized admin of this leaderboard."):
            get_leaderboard_for_admin(self.leaderboard.id, self.regular_member)

    def test_get_leaderboard_for_admin_denied_for_stranger(self):
        """A complete stranger should also be blocked from admin access."""
        with self.assertRaisesMessage(PermissionDenied, "You are not an authorized admin of this leaderboard."):
            get_leaderboard_for_admin(self.leaderboard.id, self.random_stranger)