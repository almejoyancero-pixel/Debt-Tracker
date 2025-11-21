from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Debt, Payment, Notification, AdminActivityLog


# ========================================
# CUSTOM USER ADMIN
# ========================================
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin interface for CustomUser model."""
    model = CustomUser
    
    list_display = ('username', 'full_name', 'account_type', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('account_type', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'full_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('full_name', 'account_type')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'full_name', 'account_type',
                'password1', 'password2',
                'is_staff', 'is_active'
            ),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')


# ========================================
# DEBT ADMIN
# ========================================
@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    """Admin interface for Debt model."""
    list_display = (
        'id', 'debtor', 'creditor', 'type', 'amount', 
        'product_name', 'status', 'date_created'
    )
    list_filter = ('status', 'type', 'date_created', 'creditor', 'debtor')
    search_fields = ('product_name', 'description', 'debtor__username', 'creditor__username')
    ordering = ('-date_created',)
    
    fieldsets = (
        ('Debt Relationship', {
            'fields': ('creditor', 'debtor')
        }),
        ('Debt Details', {
            'fields': ('type', 'amount', 'product_name', 'description')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'date_created', 'date_updated')
        }),
    )
    
    readonly_fields = ('date_created', 'date_updated')
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('creditor', 'debtor')


# ========================================
# PAYMENT ADMIN
# ========================================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model."""
    list_display = (
        'receipt_no', 'payer', 'debt', 'amount', 
        'method', 'status', 'created_at'
    )
    list_filter = ('status', 'method', 'created_at')
    search_fields = ('receipt_no', 'reference_number', 'payer__username')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('debt', 'payer', 'amount')
        }),
        ('Payment Method', {
            'fields': ('method', 'reference_number')
        }),
        ('Payment Proofs', {
            'fields': ('debtor_proof', 'creditor_proof')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'receipt_no', 'transaction_id', 'created_at', 'payment_date', 'verified_at')
        }),
    )
    
    readonly_fields = ('receipt_no', 'created_at')
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('debt', 'payer', 'debt__creditor', 'debt__debtor')


# ========================================
# NOTIFICATION ADMIN
# ========================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model."""
    list_display = (
        'id', 'user', 'notification_type', 'message_preview', 
        'is_read', 'created_at'
    )
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('message', 'user__username')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'message', 'related_id')
        }),
        ('Related Objects', {
            'fields': ('related_payment', 'related_debt')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    )
    
    def message_preview(self, obj):
        """Show first 50 characters of message."""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'

    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'related_payment', 'related_debt')


# ========================================
# ADMIN ACTIVITY LOG ADMIN
# ========================================
@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for AdminActivityLog model."""
    list_display = (
        'id', 'user', 'action', 'description',
        'timestamp'
    )
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'description')
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Activity Details', {
            'fields': ('user', 'action', 'description')
        }),
        ('Tracking', {
            'fields': ('timestamp',)
        }),
    )
    
    readonly_fields = ('timestamp',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user')