# Generated manually for soft delete functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0033_remove_hidden_from_creditor_fix'),
    ]

    operations = [
        migrations.AddField(
            model_name='debt',
            name='hidden_from_creditor',
            field=models.BooleanField(
                default=False, 
                help_text='If True, debt is hidden from creditor\'s dashboard (soft delete)'
            ),
        ),
    ]
