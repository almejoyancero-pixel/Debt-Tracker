# Generated migration for simplified workflow - removes debtor validation step
# This migration:
# 1. Converts all 'waiting_debtor_validation' debts to 'active'
# 2. Removes the 'waiting_debtor_validation' status from choices
# 3. Keeps debtor_acknowledged and acknowledged_at fields for backward compatibility
#    (they will be deprecated but not removed to avoid data loss)

from django.db import migrations, models


def convert_waiting_to_active(apps, schema_editor):
    """Convert all 'waiting_debtor_validation' debts to 'active' status"""
    Debt = apps.get_model('myapp', 'Debt')
    updated_count = Debt.objects.filter(status='waiting_debtor_validation').update(status='active')
    if updated_count > 0:
        print(f"✅ Converted {updated_count} debt(s) from 'waiting_debtor_validation' to 'active'")


def reverse_conversion(apps, schema_editor):
    """Reverse migration - not recommended but provided for completeness"""
    # We cannot reliably reverse this, so we'll just pass
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0013_debt_acknowledged_at_debt_debtor_acknowledged_and_more'),
    ]

    operations = [
        # First, convert existing waiting_debtor_validation debts to active
        migrations.RunPython(convert_waiting_to_active, reverse_conversion),
        
        # Update the status field choices (remove waiting_debtor_validation)
        migrations.AlterField(
            model_name='debt',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending_confirmation', 'Pending Confirmation'),
                    ('active', 'Active'),
                    ('rejected', 'Rejected'),
                    ('paid', 'Paid')
                ],
                default='pending_confirmation',
                help_text='Current status of the debt',
                max_length=30
            ),
        ),
        
        # Note: We keep debtor_acknowledged and acknowledged_at fields for backward compatibility
        # They are deprecated but not removed to preserve existing data
    ]
