import requests
from django.conf import settings
from competitions.models import Competition, Team, Match

class CompetitionSyncError(Exception):
    """Custom exception for sync failures."""
    pass

def sync_competition_matches(comp_code: str) -> dict:
    """
    Fetches match schedules and scores from api.football-data.org
    and synchronizes them with the local database.
    Returns a dictionary with synchronization statistics.
    """
    api_key = getattr(settings, 'FOOTBALL_DATA_API_KEY', None)
    if not api_key:
        raise CompetitionSyncError("API Key is missing in Django project settings.")

    url = f'https://api.football-data.org/v4/competitions/{comp_code}/matches'
    headers = {'X-Auth-Token': api_key}
    
    try:
        response = requests.get(url, headers=headers)
    except requests.RequestException as e:
        raise CompetitionSyncError(f"HTTP Request failed: {e}")

    if response.status_code != 200:
        raise CompetitionSyncError(f"API Error: Received status code {response.status_code}")

    data = response.json()
    matches = data.get('matches', [])

    if not matches:
        return {"competition_name": None, "created": 0, "updated": 0, "no_matches": True}

    comp_id = data.get('competition', {}).get('id')
    try:
        competition = Competition.objects.get(api_id=comp_id)
    except Competition.DoesNotExist:
        raise Competition.DoesNotExist(
            f"Competition with API ID {comp_id} not found in database. "
            f"Execute 'setup_competition --code={comp_code}' first."
        )

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

    return {
        "competition_name": competition.name,
        "created": matches_created,
        "updated": matches_updated,
        "no_matches": False
    }

def setup_competition_and_teams(comp_code: str) -> dict:
    """
    Fetches competition details and all qualified teams from api.football-data.org.
    Creates or updates the Competition and Team models.
    Returns a dictionary with setup statistics.
    """
    api_key = getattr(settings, 'FOOTBALL_DATA_API_KEY', None)
    if not api_key:
        raise CompetitionSyncError("API Key is missing in Django project settings.")

    url = f'https://api.football-data.org/v4/competitions/{comp_code}/teams'
    headers = {'X-Auth-Token': api_key}

    try:
        response = requests.get(url, headers=headers)
    except requests.RequestException as e:
        raise CompetitionSyncError(f"HTTP Request failed: {e}")

    if response.status_code != 200:
        raise CompetitionSyncError(f"API Error: Received status code {response.status_code}")

    data = response.json()
    comp_data = data.get('competition', {})
    season_data = data.get('season', {})
    teams_data = data.get('teams', [])

    if not comp_data:
        raise CompetitionSyncError(f"No competition data returned for code '{comp_code}'.")

    competition, comp_created = Competition.objects.update_or_create(
        api_id=comp_data.get('id'),
        defaults={
            'name': comp_data.get('name'),
            'code': comp_data.get('code'),
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

    return {
        "competition_name": competition.name,
        "teams_created": teams_created,
        "teams_updated": teams_updated,
    }