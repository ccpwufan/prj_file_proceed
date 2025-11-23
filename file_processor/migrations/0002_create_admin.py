from django.db import migrations


def create_admin(apps, schema_editor):
    # Use the historical version of the User model
    User = apps.get_model('auth', 'User')
    username = 'admin1'
    email = 'admin1@example.com'
    password = 'admin1'

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)


def remove_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username='admin1').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('file_processor', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_admin, reverse_code=remove_admin),
    ]
