import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from competitions.models import Competition, Team, Match 

class Command(BaseCommand):
    help = 'Frequent update: Fetches match schedules and final scores for a specific competition code'

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
            self.stdout.write(self.style.ERROR("API Key is missing in Django project settings"))
            return

        url = f'https://api.football-data.org/v4/competitions/{comp_code}/matches'
        headers = {'X-Auth-Token': api_key}

        self.stdout.write(f"Fetching match schedules and live statistics for '{comp_code}'...")
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"API Error: {response.status_code}"))
            return

        data = response.json()
        matches = data.get('matches', [])

        if not matches:
            self.stdout.write(self.style.WARNING(f"No matches found in the API response for '{comp_code}'."))
            return

        comp_id = data.get('competition', {}).get('id')
        try:
            competition = Competition.objects.get(api_id=comp_id)
        except Competition.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f"Competition with API ID {comp_id} not found in database. "
                f"Please execute 'setup_competition --code={comp_code}' first!"
            ))
            return

        teams_cache = {team.api_id: team for team in Team.objects.all()}

        matches_created = 0
        matches_updated = 0

        for m in matches:
            
            home_id = m.get('homeTeam', {}).get('id') if m.get('homeTeam') else None
            away_id = m.get('awayTeam', {}).get('id') if m.get('awayTeam') else None

           
            home_team = teams_cache.get(home_id) if home_id else None
            away_team = teams_cache.get(away_id) if away_id else None

            
            score_data = m.get('score', {})
            duration = score_data.get('duration', 'REGULAR')
            full_time = score_data.get('fullTime', {})
            regular_time = score_data.get('regularTime', {})
            penalties = score_data.get('penalties', {})

       
            h_90, a_90 = None, None
            h_120, a_120 = None, None
            h_pen, a_pen = None, None

            if m.get('status') == 'FINISHED':
                if duration == 'REGULAR':
                    h_90 = full_time.get('home')
                    a_90 = full_time.get('away')
                elif duration in ['EXTRA_TIME', 'PENALTY_SHOOTOUT']:
                    h_90 = regular_time.get('home') if regular_time.get('home') is not None else full_time.get('home')
                    a_90 = regular_time.get('away') if regular_time.get('away') is not None else full_time.get('away')
                    h_120 = full_time.get('home')
                    a_120 = full_time.get('away')

                    if duration == 'PENALTY_SHOOTOUT':
                        h_pen = penalties.get('home')
                        a_pen = penalties.get('away')

            match_obj, created = Match.objects.update_or_create(
                api_id=m.get('id'),
                defaults={
                    'status': m.get('status'),
                    'kickoff_time': m.get('utcDate'),
                    'competition': competition,
                    'stage': m.get('stage'),
                    'group': m.get('group'), 
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score_90': h_90,
                    'away_score_90': a_90,
                    'home_score_120': h_120,
                    'away_score_120': a_120,
                    'home_penalties': h_pen,
                    'away_penalties': a_pen,
                }
            )

            if created:
                matches_created += 1
            else:
                matches_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Synchronized matches for '{competition.name}'.\n"
            f"Matches Created: {matches_created} | Matches Updated: {matches_updated}"
        ))