from django.db import transaction
from competitions.models import Competition, Match
from predictions.models import RegistrationForCompetition, Prediction


def calculate_prediction_points(predicted_home, predicted_away, actual_home, actual_away):
    """
    Calculates points for a single prediction.
    - 3 points for the exact score (e.g., prediction 2:1, actual score 2:1)
    - 1 point for correctly guessing the outcome (win/draw/loss)
    - 0 points in other cases
    """
    #
    if actual_home is None or actual_away is None:
        return 0

    if predicted_home == actual_home and predicted_away == actual_away:
        return 3
    
    pred_diff = predicted_home - predicted_away
    actual_diff = actual_home - actual_away
    
    if (pred_diff > 0 and actual_diff > 0) or \
       (pred_diff < 0 and actual_diff < 0) or \
       (pred_diff == 0 and actual_diff == 0):
        return 1
        
    return 0


def evaluate_competition_predictions(competition_code):
    """
    Evaluates all unevaluated predictions for a given competition.
    Returns a tuple (number of updated predictions, number of updated registrations).
    Raises Competition.DoesNotExist if the code is invalid.
    """
    competition = Competition.objects.get(code=competition_code)

    finished_matches = Match.objects.filter(
        competition=competition,
        status='FINISHED',
        home_score_90__isnull=False,
        away_score_90__isnull=False
    )

    if not finished_matches.exists():
        return 0, 0

    with transaction.atomic():
        registrations = RegistrationForCompetition.objects.filter(competition=competition)
        
        predictions_to_update = []
        registrations_to_update = []

        for registration in registrations:
            predictions = Prediction.objects.filter(
                registration=registration,
                match__in=finished_matches,
                evaluated=False
            )
            
            if not predictions.exists():
                continue

            points_earned = 0
            for pred in predictions:
                points = calculate_prediction_points(
                    pred.home_score_prediction,
                    pred.away_score_prediction,
                    pred.match.home_score_90,
                    pred.match.away_score_90
                )
                
                points_earned += points
                pred.evaluated = True
                predictions_to_update.append(pred)
                
            if points_earned > 0 or predictions.exists():
                registration.points += points_earned
                registrations_to_update.append(registration)
        
        if predictions_to_update:
            Prediction.objects.bulk_update(predictions_to_update, ['evaluated'])
        
        if registrations_to_update:
            RegistrationForCompetition.objects.bulk_update(registrations_to_update, ['points'])

    return len(predictions_to_update), len(registrations_to_update)