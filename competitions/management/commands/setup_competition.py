import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from competitions.models import Competition, Team

class Command(BaseCommand):
    help = 'One-time setup: Fetches competition details and all qualified teams for a specific competition code'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            default='WC',
            help='The competition code from the API (e.g., WC, CL, PL, EC)'
        )

    def handle(self, *args, **options):
        comp_code = options['code']
        api_key = settings.FOOTBALL_DATA_API_KEY

        if not api_key:
            self.stdout.write(self.style.ERROR("API Key is missing in Django settings."))
            return

        url = f'https://api.football-data.org/v4/competitions/{comp_code}/teams'
        headers = {'X-Auth-Token': api_key}

        self.stdout.write(f"Connecting to football-data.org to fetch teams for '{comp_code}'...")
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"API Error: {response.status_code}"))
            return

        data = response.json()
        comp_data = data.get('competition', {})
        season_data = data.get('season', {})
        teams_data = data.get('teams', [])

        if not comp_data:
            self.stdout.write(self.style.ERROR(f"No competition data returned for code '{comp_code}'."))
            return

        self.stdout.write(f"Synchronizing competition metadata: {comp_data.get('name')}...")
        competition, comp_created = Competition.objects.update_or_create(
            api_id=comp_data.get('id'),
            defaults={
                'name': comp_data.get('name'),
                'emblem': comp_data.get('emblem'),
                'season_api_id': season_data.get('id'),
                'date_start': season_data.get('startDate'),
                'date_finish': season_data.get('endDate'),
            }
        )

        teams_created = 0
        teams_updated = 0

        for t in teams_data:
            team, created = Team.objects.update_or_create(
                api_id=t.get('id'),
                defaults={
                    'name': t.get('name'),
                    'code': t.get('tla'),
                    'emblem': t.get('crest')
                }
            )
            
            competition.teams.add(team)
            
            if created:
                teams_created += 1
            else:
                teams_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Competition '{competition.name}' is fully configured.\n"
            f"Teams Created: {teams_created} | Teams Updated: {teams_updated}"
        ))