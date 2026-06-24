from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from unittest.mock import patch, Mock
import requests
from datetime import date

from competitions.models import Competition, Team, Match
from predictions.models import RegistrationForCompetition 
from leaderboards.models import Leaderboard, RegistrationForLeaderboard

from competitions.services import (
    leave_competition,
    sync_competition_matches,
    setup_competition_and_teams,
    CompetitionSyncError
)

User = get_user_model()

class LeaveCompetitionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        self.competition = Competition.objects.create(
            api_id=1000, 
            season_api_id=2024,
            name="World Cup", 
            code="WC",
            date_start=date(2026, 6, 11),
            date_finish=date(2026, 7, 19),
            emblem="https://example.com/wc_logo.png"
        )
        
        self.registration = RegistrationForCompetition.objects.create(
            user=self.user, competition=self.competition
        )

    def test_leave_competition_success_no_leaderboards(self):
        leave_competition(user=self.user, competition=self.competition)
        has_registration = RegistrationForCompetition.objects.filter(id=self.registration.id).exists()
        self.assertFalse(has_registration)

    def test_leave_competition_success_is_only_member_of_leaderboard(self):
        leaderboard = Leaderboard.objects.create(name="Test League", competition=self.competition)
        RegistrationForLeaderboard.objects.create(
            leaderboard=leaderboard,
            competition_registration=self.registration,
            is_admin=False
        )
        
        leave_competition(user=self.user, competition=self.competition)
        self.assertFalse(RegistrationForCompetition.objects.filter(id=self.registration.id).exists())

    def test_leave_competition_fails_when_admin_of_leaderboard(self):
        leaderboard = Leaderboard.objects.create(name="Test League", competition=self.competition)
        RegistrationForLeaderboard.objects.create(
            leaderboard=leaderboard,
            competition_registration=self.registration,
            is_admin=True
        )
        
        with self.assertRaises(ValidationError) as context:
            leave_competition(user=self.user, competition=self.competition)
            
        self.assertIn("You cannot leave this competition because you are an administrator", str(context.exception))
        self.assertTrue(RegistrationForCompetition.objects.filter(id=self.registration.id).exists())

    def test_leave_competition_does_nothing_if_not_registered(self):
        other_user = User.objects.create_user(username='other', password='123')
        result = leave_competition(user=other_user, competition=self.competition)
        self.assertIsNone(result)


@override_settings(FOOTBALL_DATA_API_KEY='fake-api-key')
class CompetitionSyncServicesTests(TestCase):
    
    def setUp(self):
        
        self.api_teams_response = {
            "competition": {"id": 2001, "name": "Champions League", "code": "CL", "emblem": "https://api.com/cl.png"},
            "season": {"id": 1, "startDate": "2023-09-01", "endDate": "2024-06-01"},
            "teams": [
                {"id": 65, "name": "Manchester City", "tla": "MCI", "crest": "https://api.com/mci.png"},
                {"id": 86, "name": "Real Madrid", "tla": "RMA", "crest": "https://api.com/rma.png"}
            ]
        }

        self.api_matches_response = {
            "competition": {"id": 2001},
            "matches": [
                {
                    "id": 999,
                    "status": "FINISHED",
                    "utcDate": "2023-10-10T19:00:00Z",
                    "stage": "GROUP_STAGE",
                    "group": "GROUP_A",
                    "homeTeam": {"id": 65},
                    "awayTeam": {"id": 86},
                    "score": {
                        "duration": "REGULAR",
                        "fullTime": {"home": 2, "away": 1}
                    }
                }
            ]
        }

    @patch('competitions.services.requests.get')
    def test_setup_competition_and_teams_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_teams_response
        mock_get.return_value = mock_response

        stats = setup_competition_and_teams("CL")

        self.assertEqual(stats['competition_name'], "Champions League")
        self.assertEqual(stats['teams_created'], 2)
        self.assertEqual(Competition.objects.count(), 1)
        self.assertEqual(Team.objects.count(), 2)
        
        
        comp = Competition.objects.get(code="CL")
        self.assertEqual(comp.season_api_id, 1)
        self.assertEqual(str(comp.date_start), "2023-09-01")

    @override_settings(FOOTBALL_DATA_API_KEY=None)
    def test_setup_missing_api_key_raises_error(self):
        with self.assertRaisesMessage(CompetitionSyncError, "API Key is missing"):
            setup_competition_and_teams("CL")

    @patch('competitions.services.requests.get')
    def test_setup_api_http_error_raises_exception(self, mock_get):
        mock_get.side_effect = requests.RequestException("Connection timeout")
        
        with self.assertRaises(CompetitionSyncError):
            setup_competition_and_teams("CL")

    @patch('competitions.services.requests.get')
    def test_sync_matches_success(self, mock_get):
        
        comp = Competition.objects.create(
            api_id=2001, 
            season_api_id=1,
            name="Champions League", 
            code="CL",
            date_start=date(2023, 9, 1),
            date_finish=date(2024, 6, 1),
            emblem="https://example.com/cl.png"
        )
        mci = Team.objects.create(
            api_id=65, 
            name="Manchester City", 
            code="MCI", 
            emblem="https://example.com/mci.png"
        )
        rma = Team.objects.create(
            api_id=86, 
            name="Real Madrid", 
            code="RMA", 
            emblem="https://example.com/rma.png"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_matches_response
        mock_get.return_value = mock_response

        stats = sync_competition_matches("CL")

        self.assertEqual(stats['created'], 1)
        self.assertFalse(stats['no_matches'])

        match = Match.objects.get(api_id=999)
        self.assertEqual(match.competition, comp)
        self.assertEqual(match.home_team, mci)
        self.assertEqual(match.away_team, rma)
        self.assertEqual(match.home_score_90, 2)
        self.assertEqual(match.away_score_90, 1)

    @patch('competitions.services.requests.get')
    def test_sync_matches_competition_not_found(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.api_matches_response
        mock_get.return_value = mock_response

        with self.assertRaises(Competition.DoesNotExist):
            sync_competition_matches("CL")