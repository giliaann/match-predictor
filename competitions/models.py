from django.db import models
    
class Team(models.Model):

    api_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=16)
    emblem = models.URLField()
    
    def __str__(self):
        return self.name

class Competition(models.Model):
    
    api_id = models.BigIntegerField(unique=True)
    season_api_id = models.BigIntegerField()
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=16, unique=True, null=True, blank=True)
    date_start = models.DateField()
    date_finish = models.DateField()
    emblem = models.URLField()

    teams = models.ManyToManyField(Team, related_name='competitions', blank=True)

    def __str__(self):
        return f'{self.name} - {self.date_start.year}'


class Match(models.Model):

    api_id = models.BigIntegerField(unique=True)

    status = models.CharField(max_length=32)
    kickoff_time = models.DateTimeField()

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='matches')
    stage = models.CharField(max_length=64, null=True, blank=True)
    group = models.CharField(max_length=32, null=True, blank=True)

    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches', null=True, blank=True)
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches', null=True, blank=True)

    home_score_90 = models.SmallIntegerField(null=True, blank=True)
    away_score_90 = models.SmallIntegerField(null=True, blank=True)

    home_score_120 = models.SmallIntegerField(null=True, blank=True)
    away_score_120 = models.SmallIntegerField(null=True, blank=True)

    home_penalties = models.SmallIntegerField(null=True, blank=True)
    away_penalties = models.SmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.home_team} vs {self.away_team} - {self.competition}'


