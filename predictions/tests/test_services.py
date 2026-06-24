from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, date
import unittest

from competitions.models import Competition, Match, Team
from predictions.models import RegistrationForCompetition, Prediction
from predictions.services import (
    join_competition,
    process_match_predictions,
    calculate_prediction_points,
    evaluate_competition_predictions
)

User = get_user_model()

class PredictionServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='predictor', password='123')
        
        # Create Competition
        self.comp = Competition.objects.create(
            api_id=1, season_api_id=2024, name="Premier League", code="PL",
            date_start=date(2024, 8, 1), date_finish=date(2025, 5, 1), emblem="url"
        )
        
        # Create Teams
        self.team_a = Team.objects.create(api_id=10, name="Team A", code="TA")
        self.team_b = Team.objects.create(api_id=11, name="Team B", code="TB")
        
        # Create Matches
        now = timezone.now()
        
        # Match in the future (can be predicted)
        self.match_future = Match.objects.create(
            api_id=100, competition=self.comp, status="SCHEDULED", 
            kickoff_time=now + timedelta(days=1),
            home_team=self.team_a, away_team=self.team_b
        )
        
        # Match that has finished (for evaluation)
        self.match_finished = Match.objects.create(
            api_id=101, competition=self.comp, status="FINISHED", 
            kickoff_time=now - timedelta(days=2),
            home_team=self.team_a, away_team=self.team_b,
            home_score_90=2, away_score_90=1
        )
        
        # Create Registration
        self.registration, _ = join_competition(self.user, self.comp)


    # --- JOIN COMPETITION TESTS ---
    
    def test_join_competition_creates_new(self):
        """Should create a new registration if one doesn't exist."""
        new_user = User.objects.create_user(username='new_guy', password='123')
        reg, created = join_competition(new_user, self.comp)
        
        self.assertTrue(created)
        self.assertEqual(reg.user, new_user)
        self.assertEqual(reg.competition, self.comp)

    def test_join_competition_fetches_existing(self):
        """Should fetch the existing registration without creating a duplicate."""
        reg, created = join_competition(self.user, self.comp)
        
        self.assertFalse(created)
        self.assertEqual(reg, self.registration)


    # --- CALCULATE POINTS TESTS ---
    
    def test_calculate_prediction_points_exact_score(self):
        """3 points for guessing the exact score."""
        self.assertEqual(calculate_prediction_points(2, 1, 2, 1), 3)
        self.assertEqual(calculate_prediction_points(0, 0, 0, 0), 3)

    def test_calculate_prediction_points_correct_outcome(self):
        """1 point for guessing the correct winner or a draw, but wrong score."""
        # Correct winner (Home)
        self.assertEqual(calculate_prediction_points(3, 0, 2, 1), 1)
        # Correct winner (Away)
        self.assertEqual(calculate_prediction_points(0, 1, 1, 3), 1)
        # Correct outcome (Draw)
        self.assertEqual(calculate_prediction_points(1, 1, 2, 2), 1)

    def test_calculate_prediction_points_wrong_outcome(self):
        """0 points for completely missing the outcome."""
        self.assertEqual(calculate_prediction_points(2, 1, 1, 2), 0) # Guessed home win, away won
        self.assertEqual(calculate_prediction_points(1, 1, 2, 0), 0) # Guessed draw, home won

    def test_calculate_prediction_points_none_actuals(self):
        """0 points if the actual score hasn't been recorded yet."""
        self.assertEqual(calculate_prediction_points(2, 1, None, None), 0)


    # --- PROCESS PREDICTIONS TESTS ---
    
    def test_process_match_predictions_length_mismatch(self):
        """Raises ValidationError if the form lists are not identical in length."""
        with self.assertRaises(ValidationError):
            process_match_predictions(self.registration, self.comp, [1, 2], ['1'], ['0'])

    def test_process_match_predictions_success(self):
        """Successfully creates or updates predictions for valid data."""
        # Patch 'has_started' on the Match model to strictly control it for this test
        with unittest.mock.patch('competitions.models.Match.has_started', new_callable=unittest.mock.PropertyMock) as mock_has_started:
            mock_has_started.return_value = False
            
            stats = process_match_predictions(
                self.registration, 
                self.comp, 
                match_ids=[self.match_future.id], 
                home_scores=['2'], 
                away_scores=['0']
            )
            
            self.assertEqual(stats['saved'], 1)
            self.assertEqual(stats['deleted'], 0)
            self.assertEqual(stats['incomplete'], 0)
            
        
            pred = Prediction.objects.get(registration=self.registration, match=self.match_future)
            self.assertEqual(pred.home_score_prediction, 2)
            self.assertEqual(pred.away_score_prediction, 0)

    def test_process_match_predictions_ignores_started_matches(self):
        """Does not save predictions for matches that have already started."""
        with unittest.mock.patch('competitions.models.Match.has_started', new_callable=unittest.mock.PropertyMock) as mock_has_started:
            mock_has_started.return_value = True # Simulate match is currently playing
            
            stats = process_match_predictions(
                self.registration, self.comp, [self.match_future.id], ['2'], ['0']
            )
            
            self.assertEqual(stats['saved'], 0)
            self.assertFalse(Prediction.objects.filter(registration=self.registration).exists())

    def test_process_match_predictions_deletes_empty_strings(self):
        """If empty strings are submitted, an existing prediction should be deleted."""
        # Create an existing prediction first
        Prediction.objects.create(
            registration=self.registration, match=self.match_future, 
            home_score_prediction=1, away_score_prediction=1
        )
        
        with unittest.mock.patch('competitions.models.Match.has_started', new_callable=unittest.mock.PropertyMock) as mock_has_started:
            mock_has_started.return_value = False
            
            stats = process_match_predictions(
                self.registration, self.comp, [self.match_future.id], [''], ['']
            )
            
            self.assertEqual(stats['deleted'], 1)
            self.assertFalse(Prediction.objects.filter(match=self.match_future).exists())


    # --- EVALUATE PREDICTIONS TESTS ---
    
    def test_evaluate_competition_predictions_success(self):
        """Evaluates predictions, awards points, and marks them as evaluated."""
      
        pred = Prediction.objects.create(
            registration=self.registration, match=self.match_finished, 
            home_score_prediction=2, away_score_prediction=1, evaluated=False
        )
        
        updated_preds, updated_regs = evaluate_competition_predictions(self.comp.code)
        
        self.assertEqual(updated_preds, 1)
        self.assertEqual(updated_regs, 1)
        
        # Verify prediction is flagged
        pred.refresh_from_db()
        self.assertTrue(pred.evaluated)
        
        # Verify points awarded
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.points, 3)

    def test_evaluate_competition_predictions_invalid_code(self):
        """Raises DoesNotExist if an invalid competition code is passed."""
        with self.assertRaises(Competition.DoesNotExist):
            evaluate_competition_predictions("INVALID_CODE")
            
    def test_evaluate_competition_predictions_no_finished_matches(self):
        """Returns zeros if there are no finished matches to evaluate."""
        self.match_finished.status = "SCHEDULED"
        self.match_finished.save()
        
        updated_preds, updated_regs = evaluate_competition_predictions(self.comp.code)
        
        self.assertEqual(updated_preds, 0)
        self.assertEqual(updated_regs, 0)