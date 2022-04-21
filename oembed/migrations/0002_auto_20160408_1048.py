# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('oembed', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='storedoembed',
            options={'ordering': ('-max_width',), 'verbose_name': 'Stored OEmbed', 'verbose_name_plural': 'Stored OEmbeds'},
        ),
        migrations.AlterField(
            model_name='storedoembed',
            name='date_added',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='date added'),
        ),
    ]
