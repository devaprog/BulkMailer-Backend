# Generated by Django 4.1.4 on 2023-03-15 17:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mailer", "0003_alter_template_template"),
    ]

    operations = [
        migrations.AlterField(
            model_name="group_details",
            name="email",
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name="group_details",
            name="gender",
            field=models.CharField(
                choices=[("Male", "Male"), ("Female", "Female"), ("Others", "Others")],
                max_length=200,
                null=True,
            ),
        ),
    ]
