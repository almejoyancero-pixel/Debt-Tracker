"""
URL Configuration for Debt Tracker System
==========================================

This module defines all URL patterns for the application.
Routes are organized by functionality:
- Authentication (login, register, logout)
- Dashboards (role-based)
- Creditor actions (add debts, manage debtors)
- Debtor actions (confirm, reject, pay debts)
"""

from django.urls import path
from . import views


# Application namespace
app_name = 'myapp'

urlpatterns = [
    # ========================================
    # HOME & AUTHENTICATION
    # ========================================
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ========================================
    # ROLE-BASED DASHBOARD
    # ========================================
    # Main dashboard - redirects based on user role
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Specific role dashboards
    path('creditor/dashboard/', views.creditor_dashboard, name='creditor_dashboard'),
    path('debtor/dashboard/', views.debtor_dashboard, name='debtor_dashboard'),
    
    # ========================================
    # CREDITOR ACTIONS
    # ========================================
    # Pending confirmations
    path('creditor/pending-confirmation/', views.pending_confirmation, name='pending_confirmation'),
    # Add new debt
    path('add-debt/', views.add_debt, name='add_debt'),
    
    # Manage debtors
    path('add-debtor/', views.add_debtor, name='add_debtor'),
    path('debtor/list/', views.debtor_list, name='debtor_list'),
    
    # Debt management
    path('debt/<int:id>/edit/', views.edit_debt, name='edit_debt'),
    path('debt/<int:id>/delete/', views.delete_debt, name='delete_debt'),
    path('debt/<int:id>/creditor-delete/', views.creditor_delete_debt, name='creditor_delete_debt'),
    path('debt/<int:id>/mark-paid/', views.mark_as_paid, name='mark_paid'),
    path('debt/<int:id>/send-reminder/', views.send_reminder, name='send_reminder'),
    
    # Payment history
    path('payments/', views.creditor_payments, name='creditor_payments'),
    
    # All debts view (grouped by debtor)
    path('all-debts/', views.all_debts_view, name='all_debts'),
    
    # ========================================
    # DEBTOR ACTIONS
    # ========================================
    # Debt confirmation/rejection (creditor actions)
    path('confirm-debt/<int:id>/', views.confirm_debt, name='confirm_debt'),  # Legacy - redirects to upload_proof_of_release
    path('upload-proof/<int:id>/', views.upload_proof_of_release, name='upload_proof_of_release'),
    path('reject-debt/<int:id>/', views.reject_debt, name='reject_debt'),
    
    # Debtor acknowledgment - DEPRECATED (feature removed in simplified workflow)
    # path('acknowledge-receipt/<int:id>/', views.acknowledge_receipt, name='acknowledge_receipt'),
    
    # Payment processing
    path('pay-debt/<int:id>/', views.pay_debt, name='pay_debt'),
    path('payment/<int:id>/submit/', views.submit_payment, name='submit_payment'),
    
    # Online payment gateways (mock)
    path('payment/gcash/', views.gcash_payment, name='gcash_payment'),
    
    # Payment success
    path('payment/success/<int:payment_id>/', views.payment_success, name='payment_success'),
    
    # Payment receipt
    path('receipt/<int:id>/', views.view_receipt, name='view_receipt'),
    path('receipt/<int:payment_id>/download/', views.download_receipt_pdf, name='download_receipt_pdf'),

    # Payment proof URLs
path('payment/<int:payment_id>/upload-debtor-proof/', views.upload_debtor_proof, name='upload_debtor_proof'),
    path('payment/<int:payment_id>/confirm-cash/', views.confirm_cash_payment, name='confirm_cash_payment'),
    
    # Transaction history
    path('transactions/', views.transaction_history, name='transaction_history'),
    
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notification/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notification/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('notifications/clear-all/', views.clear_all_notifications, name='clear_all_notifications'),
    
    # ========================================
    # SHARED VIEWS
    # ========================================
    # View debt details
    path('debt/<int:id>/', views.debt_detail, name='debt_detail'),
    
    # User profile
    path('profile/', views.user_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # ========================================
    # SECURE FILE ACCESS
    # ========================================
    # Download proof files
    path('debt/<int:id>/download-debt-proof/', views.download_debt_proof, name='download_debt_proof'),
    path('debt/<int:id>/download-creditor-proof/', views.download_creditor_proof, name='download_creditor_proof'),
    path('debt/<int:id>/download-payment-proof/', views.download_payment_proof, name='download_payment_proof'),
    
    # View proof files inline
    path('debt/<int:id>/view-debt-proof/', views.view_debt_proof, name='view_debt_proof'),
    path('debt/<int:id>/view-creditor-proof/', views.view_creditor_proof, name='view_creditor_proof'),
    path('debt/<int:id>/view-payment-proof/', views.view_payment_proof, name='view_payment_proof'),
    
    # ========================================
    # ADMIN DASHBOARD
    # ========================================
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-users/', views.admin_users, name='admin_users'),
    path('admin-user-detail/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin-creditors/', views.admin_creditors, name='admin_creditors'),
    path('admin-debtors/', views.admin_debtors, name='admin_debtors'),
    path('admin-debts/', views.admin_debts, name='admin_debts'),
    path('admin-debt-detail/<int:debt_id>/', views.admin_debt_detail, name='admin_debt_detail'),
    path('admin-pending-confirmations/', views.admin_pending_confirmations, name='admin_pending_confirmations'),
    path('admin-activity-logs/', views.admin_activity_logs, name='admin_activity_logs'),
    path('admin-settings/', views.admin_settings, name='admin_settings'),
    path('admin-payments/', views.admin_payments, name='admin_payments'),
    path('admin-approve-payment/<int:payment_id>/', views.admin_approve_payment, name='admin_approve_payment'),
    path('admin-reject-payment/<int:payment_id>/', views.admin_reject_payment, name='admin_reject_payment'),
    path('admin-activity/', views.admin_activity, name='admin_activity'),
    
    # ========================================
    # CUSTOM CRUD INTERFACE (NEW)
    # ========================================
    # Users CRUD
    path('users/', views.users_list, name='users_list'),
    path('users/add/', views.users_add, name='users_add'),
    path('users/<int:user_id>/edit/', views.users_edit, name='users_edit'),
    path('users/<int:user_id>/delete/', views.users_delete, name='users_delete'),
    
    # Creditors CRUD
    path('creditors/', views.creditors_list, name='creditors_list'),
    path('creditors/add/', views.creditors_add, name='creditors_add'),
    path('creditors/<int:user_id>/edit/', views.creditors_edit, name='creditors_edit'),
    path('creditors/<int:user_id>/delete/', views.creditors_delete, name='creditors_delete'),
    
    # Debtors CRUD
    path('debtors/', views.debtors_list, name='debtors_list'),
    path('debtors/add/', views.debtors_add, name='debtors_add'),
    path('debtors/<int:user_id>/edit/', views.debtors_edit, name='debtors_edit'),
    path('debtors/<int:user_id>/delete/', views.debtors_delete, name='debtors_delete'),
    
    # Debts CRUD
    path('debts/', views.debts_list, name='debts_list'),
    path('debts/add/', views.debts_add, name='debts_add'),
    path('debts/<int:debt_id>/edit/', views.debts_edit, name='debts_edit'),
    path('debts/<int:debt_id>/delete/', views.debts_delete, name='debts_delete'),
]
