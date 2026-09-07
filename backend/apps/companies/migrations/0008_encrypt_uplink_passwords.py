from django.db import migrations
from apps.core.security import encrypt_secret, decrypt_secret


def encrypt_uplink_passwords(apps, schema_editor):
    RouterUplinkProfile = apps.get_model('companies', 'RouterUplinkProfile')
    for profile in RouterUplinkProfile.objects.all():
        if profile.password and not profile.password_encrypted:
            profile.password_encrypted = encrypt_secret(profile.password)
            profile.save(update_fields=['password_encrypted'])


def decrypt_uplink_passwords(apps, schema_editor):
    RouterUplinkProfile = apps.get_model('companies', 'RouterUplinkProfile')
    for profile in RouterUplinkProfile.objects.all():
        if profile.password_encrypted:
            try:
                profile.password = decrypt_secret(profile.password_encrypted)
                profile.save(update_fields=['password'])
            except Exception:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0007_routeruplinkprofile_password_encrypted'),
    ]

    operations = [
        migrations.RunPython(encrypt_uplink_passwords, decrypt_uplink_passwords),
    ]
