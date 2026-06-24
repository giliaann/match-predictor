from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta


from competitions.models import Competition, Team, Match
from predictions.models import RegistrationForCompetition, Prediction
from competitions.selectors import get_competition_details_data

User = get_user_model()

class CompetitionDetailsSelectorTests(TestCase):
    def setUp(self):
        
        self.registered_user = User.objects.create_user(username='player1', password='123')
        self.unregistered_user = User.objects.create_user(username='player2', password='123')

    
        self.competition = Competition.objects.create(
            api_id=100, 
            season_api_id=2024,
            name="Euro", 
            code="EUR",
            date_start=date(2024, 6, 14),
            date_finish=date(2024, 7, 14),
            emblem="http://example.com/logo.png"
        )

    
        self.team_a = Team.objects.create(api_id=1, name="Team A", code="TA", emblem="url")
        self.team_b = Team.objects.create(api_id=2, name="Team B", code="TB", emblem="url")
        self.team_c = Team.objects.create(api_id=3, name="Team C", code="TC", emblem="url")

    
        now = timezone.now()
        
       
        self.match_group_a = Match.objects.create(
            api_id=10, competition=self.competition, status="SCHEDULED", 
            kickoff_time=now + timedelta(days=1), stage="GROUP_STAGE", group="GROUP_A",
            home_team=self.team_a, away_team=self.team_b
        )
       
        self.match_group_b = Match.objects.create(
            api_id=11, competition=self.competition, status="SCHEDULED", 
            kickoff_time=now + timedelta(days=2), stage="GROUP_STAGE", group="GROUP_B",
            home_team=self.team_b, away_team=self.team_c
        )
       
        self.match_knockout = Match.objects.create(
            api_id=12, competition=self.competition, status="SCHEDULED", 
            kickoff_time=now + timedelta(days=5), stage="KNOCKOUT", group=None,
            home_team=self.team_a, away_team=self.team_c
        )

       
        self.registration = RegistrationForCompetition.objects.create(
            user=self.registered_user, competition=self.competition
        )
        
       
        self.prediction = Prediction.objects.create(
            registration=self.registration, 
            match=self.match_group_a, 
            home_score_prediction=2, 
            away_score_prediction=1
        )

    def test_selector_defaults_for_unregistered_user(self):
        """
        If request_stage and request_group are not provided, the function should 
        return the first stage and first group alphabetically, and not attach predictions.
        """
        data = get_competition_details_data(
            competition=self.competition, 
            user=self.unregistered_user
        )

        self.assertFalse(data['is_registered'])
        self.assertEqual(data['all_stages'], ['GROUP_STAGE', 'KNOCKOUT'])
        self.assertEqual(data['current_stage'], 'GROUP_STAGE')
        self.assertEqual(data['all_groups'], ['GROUP_A', 'GROUP_B'])
        self.assertEqual(data['current_group'], 'GROUP_A')
        
        # Only the Group A match should be returned
        self.assertEqual(len(data['matches']), 1)
        self.assertEqual(data['matches'][0], self.match_group_a)
        
        # Unregistered user should not have the user_prediction attribute
        self.assertIsNone(getattr(data['matches'][0], 'user_prediction', None))

    def test_selector_with_explicit_stage_and_group(self):
        """The function should correctly filter matches by the given stage and group."""
        data = get_competition_details_data(
            competition=self.competition, 
            user=self.unregistered_user,
            request_stage='GROUP_STAGE',
            request_group='GROUP_B'
        )

        self.assertEqual(data['current_stage'], 'GROUP_STAGE')
        self.assertEqual(data['current_group'], 'GROUP_B')
        self.assertEqual(len(data['matches']), 1)
        self.assertEqual(data['matches'][0], self.match_group_b)

    def test_selector_with_knockout_stage(self):
        """The function should handle a stage without assigned groups (group=None)."""
        data = get_competition_details_data(
            competition=self.competition, 
            user=self.unregistered_user,
            request_stage='KNOCKOUT'
        )

        self.assertEqual(data['current_stage'], 'KNOCKOUT')
        self.assertEqual(data['all_groups'], [])  
        self.assertIsNone(data['current_group'])
        
        self.assertEqual(len(data['matches']), 1)
        self.assertEqual(data['matches'][0], self.match_knockout)

    def test_selector_attaches_predictions_for_registered_user(self):
        """
        A registered user with saved predictions should receive matches
        with the injected `user_prediction` attribute.
        """
        data = get_competition_details_data(
            competition=self.competition, 
            user=self.registered_user,
            request_stage='GROUP_STAGE',
            request_group='GROUP_A'
        )

        self.assertTrue(data['is_registered'])
        match = data['matches'][0]
        
   
        self.assertTrue(hasattr(match, 'user_prediction'))
        self.assertEqual(match.user_prediction, self.prediction)
        
      
        self.assertEqual(match.user_prediction.home_score_prediction, 2)

    def test_selector_handles_empty_competition(self):
        """If the competition doesn't have any generated matches yet, the selector shouldn't throw an error."""
        empty_comp = Competition.objects.create(
            api_id=999, season_api_id=2025, name="Empty Cup", 
            date_start=date(2025, 1, 1), date_finish=date(2025, 2, 1), emblem="url"
        )
        
        data = get_competition_details_data(
            competition=empty_comp, 
            user=self.unregistered_user
        )

        self.assertEqual(data['all_stages'], [])
        self.assertIsNone(data['current_stage'])
        self.assertEqual(data['all_groups'], [])
        self.assertIsNone(data['current_group'])
        self.assertEqual(list(data['matches']), [])
        self.assertFalse(data['is_registered'])