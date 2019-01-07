# Generated by Django 2.1.4 on 2019-01-07 23:47

from django.conf import settings
from django.db import migrations, models
import filmdemocracy.socialclub.models
import markdownx.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Club',
            fields=[
                ('id', models.CharField(max_length=5, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=25, verbose_name='Club name')),
                ('short_description', models.CharField(max_length=100, verbose_name='Short club description')),
                ('club_panel', markdownx.models.MarkdownxField(blank=True, default='', max_length=1000, null=True, verbose_name='Club panel: description, rules, etc. (optional)')),
                ('logo', models.ImageField(blank=True, null=True, upload_to=filmdemocracy.socialclub.models.get_club_logo_path, verbose_name='club logo')),
                ('admin_users', models.ManyToManyField(related_name='admin_users', to=settings.AUTH_USER_MODEL)),
                ('users', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
