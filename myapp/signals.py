"""
Django signals for the Debt Tracker application.

This module contains signal handlers that automatically manage database operations,
such as resetting the auto-increment counter when all debts are deleted.

⚠️ WARNING: The renumbering functionality can cause serious data integrity issues.
Use with extreme caution and only if you fully understand the implications.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import connection, transaction
from .models import Debt


# Configuration flag - Set to False to disable renumbering
ENABLE_DEBT_RENUMBERING = False  # ⚠️ Change to True to enable (NOT RECOMMENDED)


@receiver(post_delete, sender=Debt)
def reset_debt_id_on_empty_table(sender, instance, **kwargs):
    """
    Reset the auto-increment counter for Debt ID when the table becomes empty.
    
    This signal is triggered after a Debt object is deleted. It checks if the
    Debt table is now empty, and if so, resets the auto-increment counter to 1.
    
    This ensures that when all debts are deleted, the next new debt will start
    with ID = 1 instead of continuing from the last deleted ID.
    
    Args:
        sender: The model class (Debt)
        instance: The deleted Debt instance
        **kwargs: Additional keyword arguments from the signal
    
    Safety:
        - Only executes when table is completely empty
        - Uses database-specific SQL commands
        - Wrapped in try-except to prevent crashes
        - Only affects the Debt table
    """
    # Check if the Debt table is now empty
    if Debt.objects.count() == 0:
        try:
            with connection.cursor() as cursor:
                # Get the database engine type
                db_vendor = connection.vendor
                
                if db_vendor == 'mysql':
                    # MySQL/MariaDB: Reset auto-increment to 1
                    cursor.execute("ALTER TABLE myapp_debt AUTO_INCREMENT = 1")
                    print("✅ Debt ID auto-increment reset to 1 (MySQL)")
                    
                elif db_vendor == 'postgresql':
                    # PostgreSQL: Reset sequence to 1
                    cursor.execute("ALTER SEQUENCE myapp_debt_id_seq RESTART WITH 1")
                    print("✅ Debt ID auto-increment reset to 1 (PostgreSQL)")
                    
                elif db_vendor == 'sqlite':
                    # SQLite: Delete from sqlite_sequence table
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='myapp_debt'")
                    print("✅ Debt ID auto-increment reset to 1 (SQLite)")
                    
                else:
                    print(f"⚠️ Auto-increment reset not implemented for {db_vendor}")
                    
        except Exception as e:
            # Log error but don't crash the application
            print(f"⚠️ Error resetting Debt ID auto-increment: {e}")
            # The deletion still succeeds even if reset fails


@receiver(post_delete, sender=Debt)
def renumber_debt_ids(sender, instance, **kwargs):
    """
    ⚠️ WARNING: This function renumbers all Debt IDs after a deletion.
    
    This is generally NOT RECOMMENDED because:
    1. It breaks foreign key relationships (Payments, Notifications)
    2. It violates database best practices (primary keys should be immutable)
    3. It can cause race conditions with concurrent users
    4. It impacts performance on large datasets
    5. It breaks URL references and bookmarks
    
    ONLY enable this if you:
    - Fully understand the risks
    - Have no foreign key relationships
    - Have a single-user system
    - Have a very small dataset
    
    How it works:
    1. Gets all remaining debts ordered by current ID
    2. Temporarily disables foreign key checks
    3. Updates each debt's ID sequentially (1, 2, 3...)
    4. Updates related Payment and Notification records
    5. Re-enables foreign key checks
    6. Resets auto-increment counter
    
    Args:
        sender: The model class (Debt)
        instance: The deleted Debt instance
        **kwargs: Additional keyword arguments from the signal
    """
    # Check if renumbering is enabled
    if not ENABLE_DEBT_RENUMBERING:
        return  # Exit early if disabled
    
    # Don't renumber if table is empty (handled by other signal)
    if Debt.objects.count() == 0:
        return
    
    try:
        with transaction.atomic():
            # Import here to avoid circular imports
            from .models import Payment, Notification
            
            # Get all remaining debts ordered by ID
            debts = list(Debt.objects.all().order_by('id'))
            
            if not debts:
                return
            
            # Disable foreign key checks temporarily
            with connection.cursor() as cursor:
                db_vendor = connection.vendor
                
                if db_vendor == 'mysql':
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                elif db_vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys = OFF")
                elif db_vendor == 'postgresql':
                    cursor.execute("SET CONSTRAINTS ALL DEFERRED")
            
            # Renumber debts sequentially
            for new_id, debt in enumerate(debts, start=1):
                old_id = debt.id
                
                if old_id != new_id:
                    # Update related Payment records
                    Payment.objects.filter(debt_id=old_id).update(debt_id=new_id)
                    
                    # Update related Notification records
                    Notification.objects.filter(related_debt_id=old_id).update(related_debt_id=new_id)
                    
                    # Update the debt's ID using raw SQL (can't use ORM for primary key)
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE myapp_debt SET id = %s WHERE id = %s",
                            [new_id, old_id]
                        )
                    
                    print(f"🔄 Renumbered Debt ID {old_id} → {new_id}")
            
            # Re-enable foreign key checks
            with connection.cursor() as cursor:
                if db_vendor == 'mysql':
                    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                    # Reset auto-increment to next number
                    next_id = len(debts) + 1
                    cursor.execute(f"ALTER TABLE myapp_debt AUTO_INCREMENT = {next_id}")
                    
                elif db_vendor == 'sqlite':
                    cursor.execute("PRAGMA foreign_keys = ON")
                    # Update sqlite_sequence
                    next_id = len(debts) + 1
                    cursor.execute(
                        "UPDATE sqlite_sequence SET seq = ? WHERE name = 'myapp_debt'",
                        [next_id - 1]
                    )
                    
                elif db_vendor == 'postgresql':
                    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                    # Reset sequence
                    next_id = len(debts) + 1
                    cursor.execute(f"ALTER SEQUENCE myapp_debt_id_seq RESTART WITH {next_id}")
            
            print(f"✅ Successfully renumbered {len(debts)} debts")
            
    except Exception as e:
        print(f"❌ Error renumbering Debt IDs: {e}")
        # Transaction will rollback automatically
        raise  # Re-raise to prevent deletion if renumbering fails
