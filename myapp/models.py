from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid
import secrets


# ========================================
# CUSTOM USER MANAGER
# ========================================
class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser model.
    Handles user creation with role-based account types.
    """
    def create_user(self, username, full_name, account_type, password=None, **extra_fields):
        """Create and return a regular user with an account type."""
        if not username:
            raise ValueError("The username field is required")
        if not full_name:
            raise ValueError("The full name field is required")
        if account_type not in ['creditor', 'debtor', 'admin']:
            raise ValueError("Account type must be either 'creditor', 'debtor', or 'admin'")

        user = self.model(
            username=username,
            full_name=full_name,
            account_type=account_type,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, full_name, password=None, **extra_fields):
        """Create and return a superuser with admin account type."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        # Set account type to 'admin' for superusers
        return self.create_user(username, full_name, 'admin', password, **extra_fields)


# ========================================
# CUSTOM USER MODEL
# ========================================
class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with role-based authentication.
    Supports three user types: Creditor, Debtor, and Admin.
    """
    ROLE_CHOICES = [
        ('creditor', 'Creditor'),
        ('debtor', 'Debtor'),
        ('admin', 'Admin'),
    ]

    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="Required. 150 characters or fewer. Unique username."
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Full name of the user"
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email address (optional)"
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text="Profile picture (optional)"
    )
    profile_summary = models.TextField(
        blank=True,
        null=True,
        help_text="Short bio or profile summary (optional)"
    )
    account_type = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="User role: Creditor, Debtor, or Admin"
    )
    
    # Django required fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.get_account_type_display()})"

    def is_creditor(self):
        """Check if user is a creditor."""
        return self.account_type == 'creditor'

    def is_debtor(self):
        """Check if user is a debtor."""
        return self.account_type == 'debtor'

    def is_admin(self):
        """Check if user is an admin."""
        return self.account_type == 'admin'


# ========================================
# DEBT MODEL
# ========================================
class Debt(models.Model):
    """
    Debt model representing a debt relationship between creditor and debtor.
    Tracks debt type, amount, status, and lifecycle.
    """
    TYPE_CHOICES = [
        ('money', 'Money'),
        ('product', 'Product'),
    ]

    STATUS_CHOICES = [
        ('pending_confirmation', 'Pending Confirmation'),
        ('active', 'Active'),
        ('awaiting_confirmation', 'Awaiting Confirmation'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]

    # Relationships
    creditor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creditor_debts',
        help_text="User who is owed (creditor)"
    )
    debtor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debtor_debts',
        help_text="User who owes (debtor)"
    )

    # Debt Details
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='money',
        help_text="Type of debt: Money or Product"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Amount owed (for money) or estimated value (for product)"
    )
    product_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of product/item (if type is Product)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Additional details about the debt"
    )
    debt_proof = models.FileField(
        upload_to='debt_proofs/',
        blank=True,
        null=True,
        help_text="Proof of debt (photo, screenshot, or PDF) uploaded by debtor"
    )
    creditor_proof = models.FileField(
        upload_to='creditor_proofs/',
        blank=True,
        null=True,
        help_text="Proof of release - item/money was given to debtor (uploaded by creditor)"
    )
    payment_proof = models.FileField(
        upload_to='payment_proofs_debt/',
        blank=True,
        null=True,
        help_text="Proof of payment when creditor marks debt as paid (optional)"
    )
    # DEPRECATED: These fields are kept for backward compatibility only
    # The debtor acknowledgment step has been removed from the workflow
    debtor_acknowledged = models.BooleanField(
        default=False,
        help_text="[DEPRECATED] Whether debtor has acknowledged receipt of item/money"
    )
    acknowledged_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="[DEPRECATED] Date when debtor acknowledged receipt"
    )

    # Payment tracking
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total amount paid towards this debt"
    )
    
    # Status Tracking
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending_confirmation',
        help_text="Current status of the debt"
    )

    # Visibility Control
    hidden_from_debtor = models.BooleanField(
        default=False,
        help_text="If True, debt is hidden from debtor's view (soft delete)"
    )
    hidden_from_creditor = models.BooleanField(
        default=False,
        help_text="If True, debt is hidden from creditor's dashboard (soft delete)"
    )
    
    # Timestamps
    date_created = models.DateTimeField(
        auto_now_add=True,
        help_text="Date when debt was created"
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        help_text="Date when debt was last updated"
    )
    date_paid = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when debt was paid"
    )

    class Meta:
        verbose_name = 'Debt'
        verbose_name_plural = 'Debts'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['creditor', 'status']),
            models.Index(fields=['debtor', 'status']),
        ]

    def __str__(self):
        item_display = self.product_name if self.type == 'product' else f"₱{self.amount}"
        return f"{self.debtor.username} owes {self.creditor.username}: {item_display} [{self.get_status_display()}]"

    def is_pending_confirmation(self):
        """Check if debt is pending creditor confirmation."""
        return self.status == 'pending_confirmation'

    def is_waiting_validation(self):
        """Check if debt is waiting for debtor validation - DEPRECATED."""
        # This status no longer exists in the simplified workflow
        return False

    def is_active(self):
        """Check if debt is active."""
        return self.status == 'active'

    def is_paid(self):
        """Check if debt is paid."""
        return self.status == 'paid'

    def is_rejected(self):
        """Check if debt is rejected."""
        return self.status == 'rejected'

    def can_be_paid(self):
        """Check if debt can be paid (only active debts)."""
        return self.status == 'active'
    
    def can_creditor_upload_proof(self):
        """Check if creditor can upload proof of release."""
        return self.status == 'pending_confirmation'
    
    def can_debtor_acknowledge(self):
        """Check if debtor can acknowledge receipt - DEPRECATED."""
        # Feature removed - debts auto-activate when creditor uploads proof
        return False

    @property
    def balance(self):
        """Calculate the remaining balance for this debt."""
        return max(0, float(self.amount) - float(self.paid_amount))
    
    def update_payment_status(self):
        """Update the status based on payment."""
        if self.balance <= 0 and self.status == 'active':
            self.status = 'paid'
            self.date_paid = timezone.now()
            self.save()
            return True
        return False


# ========================================
# PAYMENT MODEL
# ========================================
class Payment(models.Model):
    """
    Payment model representing a payment transaction for a debt.
    Tracks payment method, amount, proof, and status.
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('gcash', 'GCash'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending_debtor_proof', 'Awaiting Debtor Proof'),
        ('pending_creditor_proof', 'Awaiting Creditor Proof'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    # Relationships
    debt = models.ForeignKey(
        Debt,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Associated debt for this payment"
    )
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_made',
        help_text="User who made the payment"
    )

    # Payment Details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Amount paid"
    )
    method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="Payment method used"
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Transaction/Reference number (optional)"
    )
    debtor_proof = models.FileField(
        upload_to='payment_proofs/debtor/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Debtor's proof of payment (for cash payments)"
    )
    creditor_proof = models.FileField(
        upload_to='payment_proofs/creditor/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Creditor's proof of receipt (for cash payments)"
    )
    payment_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when payment was completed"
    )

    # Status and Tracking
    status = models.CharField(
        max_length=30,
        choices=PAYMENT_STATUS_CHOICES,
        default='completed',
        help_text="Payment verification status"
    )
    receipt_no = models.CharField(
        max_length=50,
        unique=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique receipt number"
    )
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        default='',
        help_text="Unique transaction ID"
    )
    receipt_file = models.FileField(
        upload_to='receipts/',
        blank=True,
        null=True,
        help_text="Generated PDF receipt"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date when payment was recorded"
    )
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when payment was verified"
    )

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['debt', 'status']),
            models.Index(fields=['payer', 'created_at']),
        ]

    def __str__(self):
        return f"Payment #{self.receipt_no} - ₱{self.amount} by {self.payer.username} [{self.get_status_display()}]"

    def is_completed(self):
        """Check if payment is completed."""
        return self.status == 'completed'

    def is_pending_debtor_proof(self):
        """Check if payment is awaiting debtor proof."""
        return self.status == 'pending_debtor_proof'
    
    def is_pending_creditor_proof(self):
        """Check if payment is awaiting creditor proof."""
        return self.status == 'pending_creditor_proof'
    
    def save(self, *args, **kwargs):
        """Generate transaction ID if not present."""
        if not self.transaction_id:
            self.transaction_id = f"TXN-{secrets.token_hex(8).upper()}"
        if self.status == 'completed' and not self.payment_date:
            self.payment_date = timezone.now()
        if self.status == 'completed' and not self.verified_at:
            self.verified_at = timezone.now()
        super().save(*args, **kwargs)


# ========================================
# NOTIFICATION MODEL
# ========================================
class Notification(models.Model):
    """
    Notification model for user notifications.
    Tracks payment notifications and other system events.
    """
    NOTIFICATION_TYPES = [
        ('payment_success', 'Payment Success'),
        ('payment_received', 'Payment Received'),
        ('payment_pending', 'Payment Pending'),
        ('payment_debtor_proof_uploaded', 'Debtor Proof Uploaded'),
        ('payment_creditor_proof_uploaded', 'Creditor Proof Uploaded'),
        ('payment_completed', 'Payment Completed'),
        ('partial_payment_received', 'Partial Payment Received'),
        ('debt_confirmed', 'Debt Confirmed'),
        ('debt_rejected', 'Debt Rejected'),
        ('debt_added', 'Debt Added'),
        ('debt_pending_confirmation', 'Debt Pending Confirmation'),
        ('proof_uploaded', 'Proof Uploaded'),
        ('debt_acknowledged', 'Debt Acknowledged'),
        ('debt_active', 'Debt Active'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User who receives this notification"
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        help_text="Type of notification"
    )
    message = models.TextField(
        help_text="Notification message"
    )
    related_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="Related object ID (for generic references)"
    )
    related_payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications',
        help_text="Related payment (if applicable)"
    )
    related_debt = models.ForeignKey(
        Debt,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications',
        help_text="Related debt (if applicable)"
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether notification has been read"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When notification was created"
    )
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_notification_type_display()}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.save()


# ========================================
# ADMIN ACTIVITY LOG MODEL
# ========================================
class AdminActivityLog(models.Model):
    """
    AdminActivityLog model for tracking superuser actions.
    Records administrative activities for audit purposes.
    """
    ACTION_CHOICES = [
        ('login', 'Admin Login'),
        ('view_users', 'View Users List'),
        ('view_user_detail', 'View User Detail'),
        ('view_debts', 'View Debts List'),
        ('view_debt_detail', 'View Debt Detail'),
        ('view_payments', 'View Payments List'),
        ('approve_payment', 'Approve Payment'),
        ('reject_payment', 'Reject Payment'),
        ('view_activity', 'View Activity Log'),
        ('update_settings', 'Update Settings'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_activities',
        help_text="Admin user who performed the action"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    description = models.TextField(
        help_text="Detailed description of the action"
    )
    related_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="Related object ID (if applicable)"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="Browser user agent"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the action was performed"
    )
    
    class Meta:
        verbose_name = 'Admin Activity Log'
        verbose_name_plural = 'Admin Activity Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
