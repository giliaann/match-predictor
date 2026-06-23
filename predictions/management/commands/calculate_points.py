from django.core.management.base import BaseCommand
from competitions.models import Competition
from predictions.services import evaluate_competition_predictions

class Command(BaseCommand):
    help = 'Calculates points for all registrations in a given competition based on its code.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            help='The competition code from the API (e.g., WC, CL, PL, EC)'
        )


    def handle(self, *args, **kwargs):
        competition_code = kwargs['code']

        try:
           
            updated_preds, updated_regs = evaluate_competition_predictions(competition_code)
            
            if updated_preds == 0:
                self.stdout.write(self.style.WARNING('No new matches/predictions found to evaluate.'))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Evaluated {updated_preds} predictions and updated accounts for {updated_regs} users.'
                ))

        except Competition.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Competition with code "{competition_code}" does not exist.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An unexpected error occurred: {e}'))