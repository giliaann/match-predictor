from django.contrib import admin
from .models import Team, Match, Competition

admin.site.register(Team)
admin.site.register(Competition)
admin.site.register(Match)
