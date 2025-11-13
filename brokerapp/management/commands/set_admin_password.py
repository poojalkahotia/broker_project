 
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create or update admin password from env AUTO_ADMIN_USERNAME / AUTO_ADMIN_PASSWORD"

    def handle(self, *args, **options):
        username = os.environ.get("AUTO_ADMIN_USERNAME", "admin")
        password = os.environ.get("AUTO_ADMIN_PASSWORD")
        email = os.environ.get("AUTO_ADMIN_EMAIL", "admin@example.com")

        if not password:
            self.stderr.write(self.style.ERROR("AUTO_ADMIN_PASSWORD is not set. Aborting."))
            return

        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created admin '{username}' and set password."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated password for existing admin '{username}'."))

