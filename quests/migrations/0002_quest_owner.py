# Generated manually to align DB schema with Quest model.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
        ("quests", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="quest",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="quests",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
            ),
        ),
    ]
