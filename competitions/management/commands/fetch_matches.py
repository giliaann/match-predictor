from django.core.management.base import BaseCommand
from competitions.models import Competition
from competitions.services import sync_competition_matches, CompetitionSyncError

class Command(BaseCommand):
    help = 'Frequent update: Fetches match schedules and final scores for a specific competition code'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            required=True,
            help='The competition code from the API (e.g., WC, CL, PL, EC)'
        )

    def handle(self, *args, **options):
        comp_code = options['code']

        self.stdout.write(f"Fetching match schedules and live statistics for '{comp_code}'...")

        try:
            stats = sync_competition_matches(comp_code)
            
            if stats["no_matches"]:
                self.stdout.write(self.style.WARNING(f"No matches found in the API response for '{comp_code}'."))
                return

            self.stdout.write(self.style.SUCCESS(
                f"Synchronized matches for '{stats['competition_name']}'.\n"
                f"Matches Created: {stats['created']} | Matches Updated: {stats['updated']}"
            ))

        except Competition.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except CompetitionSyncError as e:
            self.stdout.write(self.style.ERROR(f"Sync failed: {str(e)}"))