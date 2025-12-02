"""
Management command to seed junior frontend developer benchmark data
"""
from django.core.management.base import BaseCommand
from apps.agents.synthetic_data import seed_junior_frontend_benchmarks


class Command(BaseCommand):
    help = 'Seed database with junior frontend developer benchmark data'

    def handle(self, *args, **options):
        self.stdout.write('Generating junior frontend developer benchmark data...')
        self.stdout.write('This creates 200 synthetic profiles based on market data.')
        
        count = seed_junior_frontend_benchmarks()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully generated {count} junior frontend profiles')
        )
        self.stdout.write('Benchmark cohort created: junior_frontend_2024')
