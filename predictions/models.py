from django.db import models
from django.conf import settings

class RegistrationForCompetition(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='competition_registrations')
    competition = models.ForeignKey('competitions.Competition', on_delete=models.CASCADE,related_name='registrations')
    points = models.IntegerField(default = 0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'competition'],
                name='unique_user_registration_per_competition'
            )
        ]

    def __str__(self):
        return f'{self.user.username} -> {self.competition}'
    

class Prediction(models.Model):
    
    registration = models.ForeignKey('RegistrationForCompetition', on_delete=models.CASCADE, related_name='predictions')
    match = models.ForeignKey('competitions.Match', on_delete=models.CASCADE, related_name='predictions')

    home_score_prediction = models.SmallIntegerField()
    away_score_prediction = models.SmallIntegerField()

    evaluated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        
        constraints = [
            models.UniqueConstraint(
                fields=['registration', 'match'],
                name='unique_prediction_per_match_and_registration' 
            )
        ]

    def __str__(self):
        return f'{self.registration.user.username} - {self.match} - Prediction: {self.home_score_prediction}:{self.away_score_prediction}'