from django.db import transaction
from competitions.models import Competition, Match
from predictions.models import RegistrationForCompetition, Prediction
from django.core.exceptions import ValidationError
from django.db import transaction
from competitions.models import Match
from .models import RegistrationForCompetition


def join_competition(user, competition):
    """
    Registers a user for a specific competition.
    """
    registration, created = RegistrationForCompetition.objects.get_or_create(
        user=user,
        competition=competition
    )
    return registration, created

@transaction.atomic
def process_match_predictions(registration, competition, match_ids, home_scores, away_scores):
    """
    Processes a bulk list of match predictions submitted by the user.
    Returns a dictionary with operation statistics for the view to render.
    """
    if not (len(match_ids) == len(home_scores) == len(away_scores)):
        raise ValidationError("Invalid form data. Data lists length mismatch.")

    stats = {
        'saved': 0,
        'deleted': 0,
        'incomplete': 0
    }

    for i in range(len(match_ids)):
        m_id = match_ids[i]
        h_score = home_scores[i]
        a_score = away_scores[i]

        try:
          
            match = Match.objects.get(id=m_id, competition=competition)
            
            if match.has_started:
                continue
           
            if h_score != '' and a_score != '':
                registration.predictions.update_or_create(
                    match=match,
                    defaults={
                        'home_score_prediction': int(h_score),
                        'away_score_prediction': int(a_score)
                    }
                )
                stats['saved'] += 1
    
            elif h_score == '' and a_score == '':
                deleted, _ = registration.predictions.filter(match=match).delete()
                if deleted > 0:
                    stats['deleted'] += 1

            
            else:
                stats['incomplete'] += 1

        except (Match.DoesNotExist, ValueError):
            continue

    return stats


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