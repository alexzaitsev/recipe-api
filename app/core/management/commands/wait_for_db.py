import time

from django.core.management import BaseCommand
from django.db import connections, OperationalError


# must be called Command
class Command(BaseCommand):
    """Django command to pause execution until database is available"""
    help = 'Pauses execution until database is available.'

    def handle(self, *args, **options):
        self.stdout.write('Waiting for database...')
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections['default']
            except OperationalError:
                self.stdout.write('Database unavailable, waiting 1 second...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database available!'))
