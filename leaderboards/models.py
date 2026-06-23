from django.db import models
import secrets

def generate_join_code():
    return secrets.token_hex(4).upper()

class Leaderboard(models.Model):
    name = models.CharField(max_length=128)
    
    join_code = models.CharField(max_length=16, unique=True, default=generate_join_code, )
    
    competition = models.ForeignKey('competitions.Competition', on_delete=models.CASCADE, related_name='leaderboards')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.competition.name})"


class RegistrationForLeaderboard(models.Model):
    
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE, related_name='registrations')

    competition_registration = models.ForeignKey('predictions.RegistrationForCompetition', on_delete=models.CASCADE, related_name='leaderboards')
    
    is_admin = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['leaderboard', 'competition_registration'], 
                name='unique_member_per_leaderboard'
            )
        ]

    def __str__(self):
        return f"{self.competition_registration.user.username} -> {self.leaderboard}"