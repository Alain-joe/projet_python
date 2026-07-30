import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "cemeterre_backend.settings"
)

django.setup()

from users.models import User

username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "Admin123!")

if not User.objects.filter(username=username).exists():
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name="Admin",
        last_name="System",
    )

    user.role = "admin"
    user.is_approved = True
    user.save()

    print("Superuser créé avec succès")
else:
    print("Superuser existe déjà")