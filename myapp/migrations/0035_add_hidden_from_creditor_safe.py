# Safe migration to add hidden_from_creditor field if it doesn't exist

from django.db import migrations, models, connection


def add_hidden_from_creditor_if_not_exists(apps, schema_editor):
    """
    Add hidden_from_creditor field to myapp_debt table if it doesn't exist.
    This handles the case where the field doesn't exist in production.
    """
    with connection.cursor() as cursor:
        # Check if we're using PostgreSQL or SQLite
        db_vendor = connection.vendor
        
        if db_vendor == 'postgresql':
            # PostgreSQL: Check if column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'myapp_debt' 
                AND column_name = 'hidden_from_creditor'
            """)
            column_exists = cursor.fetchone()[0] > 0
            
            if not column_exists:
                # Add the column
                cursor.execute("""
                    ALTER TABLE myapp_debt 
                    ADD COLUMN hidden_from_creditor BOOLEAN NOT NULL DEFAULT FALSE
                """)
                
        elif db_vendor == 'sqlite':
            # SQLite: Check if column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pragma_table_info('myapp_debt') 
                WHERE name = 'hidden_from_creditor'
            """)
            column_exists = cursor.fetchone()[0] > 0
            
            if not column_exists:
                # Add the column
                cursor.execute("""
                    ALTER TABLE myapp_debt 
                    ADD COLUMN hidden_from_creditor BOOLEAN NOT NULL DEFAULT 0
                """)


def remove_hidden_from_creditor_if_exists(apps, schema_editor):
    """
    Remove hidden_from_creditor field if it exists (reverse operation).
    """
    with connection.cursor() as cursor:
        db_vendor = connection.vendor
        
        if db_vendor == 'postgresql':
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'myapp_debt' 
                AND column_name = 'hidden_from_creditor'
            """)
            column_exists = cursor.fetchone()[0] > 0
            
            if column_exists:
                cursor.execute("""
                    ALTER TABLE myapp_debt 
                    DROP COLUMN hidden_from_creditor
                """)
                
        elif db_vendor == 'sqlite':
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pragma_table_info('myapp_debt') 
                WHERE name = 'hidden_from_creditor'
            """)
            column_exists = cursor.fetchone()[0] > 0
            
            if column_exists:
                # SQLite doesn't support DROP COLUMN directly, would need table recreation
                # For simplicity, we'll just pass in reverse migration
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0033_remove_hidden_from_creditor_fix'),
    ]

    operations = [
        migrations.RunPython(
            add_hidden_from_creditor_if_not_exists, 
            reverse_code=remove_hidden_from_creditor_if_exists
        ),
    ]