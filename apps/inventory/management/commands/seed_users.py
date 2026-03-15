"""
Usage: python manage.py seed_users
Creates 5 regular users and 2 employees for testing role permissions.
Safe to run multiple times — skips users that already exist.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.accounts.models import UserProfile

USERS = [
    # (username, email, password, role)
    ('ana_k',      'ana@example.com',    'password123', 'user'),
    ('giorgi_b',   'giorgi@example.com', 'password123', 'user'),
    ('nino_t',     'nino@example.com',   'password123', 'user'),
    ('luka_m',     'luka@example.com',   'password123', 'user'),
    ('mariam_j',   'mariam@example.com', 'password123', 'user'),
    ('sandro_emp', 'sandro@example.com', 'password123', 'employee'),
    ('keti_emp',   'keti@example.com',   'password123', 'employee'),
]


class Command(BaseCommand):
    help = 'Seed 5 regular users and 2 employees for permission testing.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding test users...\n')

        for username, email, password, role in USERS:
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'  skip — {username} already exists')
                continue

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            # Signal creates the profile with role='user'; update if needed
            profile = user.profile
            profile.role = role
            profile.save()

            self.stdout.write(self.style.SUCCESS(
                f'  + {username} ({role}) — password: {password}'
            ))

        self.stdout.write(self.style.SUCCESS(
            '\nDone. Log in as admin and go to /users/ to see all accounts.'
        ))
