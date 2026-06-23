from django.core.management.base import BaseCommand
from competitions.services import setup_competition_and_teams, CompetitionSyncError

class Command(BaseCommand):
    help = 'One-time setup: Fetches competition details and all qualified teams for a specific competition code'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            required=True,
            help='The competition code from the API (e.g., WC, CL, PL, EC)'
        )

    def handle(self, *args, **options):
        comp_code = options['code']

        self.stdout.write(f"Connecting to football-data.org to fetch teams for '{comp_code}'...")

        try:
            stats = setup_competition_and_teams(comp_code)
            
            self.stdout.write(self.style.SUCCESS(
                f"Competition '{stats['competition_name']}' is fully configured.\n"
                f"Teams Created: {stats['teams_created']} | Teams Updated: {stats['teams_updated']}"
            ))

        except CompetitionSyncError as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))