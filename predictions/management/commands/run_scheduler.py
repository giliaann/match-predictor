import time
import schedule
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Runs periodic tasks in the background"

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            required=True,
            help='The competition code from the API (e.g., WC, CL, PL, EC)'
        )

    def run_my_task(self, competition_code):
        self.stdout.write(self.style.SUCCESS("Running periodic task..."))
    
        call_command('fetch_matches', code=competition_code)
        call_command('calculate_points', code=competition_code)
        self.stdout.write(self.style.SUCCESS("Task completed."))

    def handle(self, *args, **kwargs):
        
        competition_code = kwargs['code']

        schedule.every(15).minutes.do(self.run_my_task, competition_code)
        
        self.stdout.write("Scheduler started. Waiting for tasks...")

        while True:
            schedule.run_pending()
            time.sleep(1)