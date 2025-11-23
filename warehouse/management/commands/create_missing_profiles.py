from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from warehouse.models import UserProfile

class Command(BaseCommand):
    help = 'Create missing UserProfile objects for all users.'

    def handle(self, *args, **options):
        User = get_user_model()
        created_count = 0
        for user in User.objects.all():
            profile, created = UserProfile.objects.get_or_create(user=user)
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} missing UserProfile(s).'))
