
"""
Views for Debt Tracker System
==============================

This module contains all view functions for the application:
- Authentication (login, logout, register)
- Role-based dashboards (creditor/debtor)
- Debt management (add, edit, delete, confirm, reject)
- Payment processing (GCash, Cash)
- Status updates and role-based access control
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import HttpResponse, FileResponse
from django.core.files.base import ContentFile
from django.conf import settings
from io import BytesIO
import os
import uuid
from datetime import datetime
from .models import CustomUser, Debt, Payment, Notification
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    DebtForm,
    AddDebtorForm,
    PaymentForm,
    PaymentMethodForm,
    PaymentProofForm
)

# PDF Generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def home_view(request):
    """Public landing page shown before login/register."""
    if request.user.is_authenticated:
        # Redirect directly to appropriate dashboard based on user type
        if request.user.is_superuser or request.user.account_type == 'admin':
            return redirect('myapp:admin_dashboard')
        elif request.user.account_type == 'creditor':
            return redirect('myapp:creditor_dashboard')
        else:
            return redirect('myapp:debtor_dashboard')

    # Unauthenticated users see the marketing landing page
    return render(request, 'index.html')


def google_verify(request):
    """Plain-text response for Google Search Console verification."""
    return HttpResponse(
        "google-site-verification: googlea318f19596005dc2.html",
        content_type="text/plain",
    )


def register_view(request):
    if request.user.is_authenticated:
        # Redirect directly to appropriate dashboard based on user type
        if request.user.is_superuser:
            return redirect('myapp:admin_dashboard')
        elif request.user.account_type == 'creditor':
            return redirect('myapp:creditor_dashboard')
        elif request.user.account_type == 'admin':
            return redirect('myapp:admin_dashboard')
        else:
            return redirect('myapp:debtor_dashboard')
    
    # Initialize context with empty values
    context = {
        'full_name': '',
        'username': '',
        'email': '',
        'account_type': '',
        'errors': {},  # Field-specific errors
        'general_error': None,  # General error message
    }
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        account_type = request.POST.get('account_type', '').strip()
        password = request.POST.get('password', '')
        
        # Update context with submitted values
        context.update({
            'full_name': full_name,
            'username': username,
            'email': email,
            'account_type': account_type,
        })
        
        errors = {}
        
        # Validate required fields
        if not full_name:
            errors['full_name'] = 'Full name is required.'
        if not username:
            errors['username'] = 'Username is required.'
        if not email:
            errors['email'] = 'Email address is required.'
        if not account_type:
            errors['account_type'] = 'Please select an account type.'
        if not password:
            errors['password'] = 'Password is required.'
        
        # Validate email format
        if email and '@' not in email:
            errors['email'] = 'Please enter a valid email address.'
        
        # Validate account type
        if account_type and account_type not in ['creditor', 'debtor']:
            errors['account_type'] = 'Invalid account type selected.'
        
        # Check if username already exists
        if username and CustomUser.objects.filter(username=username).exists():
            errors['username'] = 'Username already exists. Please choose another.'
        
        # Check if email already exists
        if email and CustomUser.objects.filter(email=email).exists():
            errors['email'] = 'Email address is already registered.'
        
        # If there are validation errors, return with errors
        if errors:
            context['errors'] = errors
            return render(request, 'register.html', context)
        
        # Try to create user
        try:
            user = CustomUser.objects.create_user(
                username=username,
                full_name=full_name,
                account_type=account_type,
                password=password,
                email=email
            )
            
            messages.success(request, f'Account created successfully! Welcome, {full_name}.')
            login(request, user)
            # Redirect based on account type
            if user.account_type == 'creditor':
                return redirect('myapp:creditor_dashboard')
            else:
                return redirect('myapp:debtor_dashboard')
        except Exception as e:
            context['general_error'] = f'Registration failed: {str(e)}'
            return render(request, 'register.html', context)
    
    return render(request, 'register.html', context)


def login_view(request):
    if request.user.is_authenticated:
        # Redirect directly to appropriate dashboard based on user type
        if request.user.is_superuser:
            return redirect('myapp:admin_dashboard')
        elif request.user.account_type == 'creditor':
            return redirect('myapp:creditor_dashboard')
        elif request.user.account_type == 'admin':
            return redirect('myapp:admin_dashboard')
        else:
            return redirect('myapp:debtor_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not all([username, password]):
            messages.error(request, 'Username and password are required.')
            return render(request, 'login.html', {
                'username': username,
            })
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.full_name}!')
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # Automatically redirect based on user's account type and superuser status
            if user.is_superuser:
                # Log admin activity
                from .models import AdminActivityLog
                AdminActivityLog.objects.create(
                    user=user,
                    action='login',
                    description=f'Admin {user.username} logged in to admin dashboard',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                return redirect('myapp:admin_dashboard')
            elif user.account_type == 'creditor':
                return redirect('myapp:creditor_dashboard')
            elif user.account_type == 'admin':
                return redirect('myapp:admin_dashboard')
            else:
                return redirect('myapp:debtor_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'login.html', {
                'username': username,
            })
    
    return render(request, 'login.html')


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('myapp:home')


@login_required
def dashboard_view(request):
    if request.user.is_superuser:
        return redirect('myapp:admin_dashboard')
    elif request.user.account_type == 'creditor':
        return redirect('myapp:creditor_dashboard')
    elif request.user.account_type == 'admin':
        return redirect('myapp:admin_dashboard')
    elif request.user.account_type == 'debtor':
        return redirect('myapp:debtor_dashboard')
    else:
        messages.error(request, "Invalid account type.")
        return redirect('myapp:login')


@login_required
def creditor_dashboard(request):
    if request.user.account_type != 'creditor':
        messages.error(request, "Access denied. Creditors only.")
        return redirect('myapp:home')
    
    search_query = request.GET.get('q', '').strip()
    
    # Get all debts for this creditor (temporarily excluding hidden filter until migration applied to production)
    debts = Debt.objects.filter(creditor=request.user).select_related('debtor')
    
    if search_query:
        debts = debts.filter(
            Q(debtor__username__icontains=search_query) |
            Q(debtor__full_name__icontains=search_query)
        )
    
    # Filter debts by status
    pending_debts = debts.filter(status='pending_confirmation')
    active_debts = debts.filter(status='active')
    awaiting_confirmation_debts = debts.filter(status='awaiting_confirmation')
    paid_debts = debts.filter(status='paid')
    rejected_debts = debts.filter(status='rejected')
    
    # Calculate totals for dashboard cards
    total_pending = sum(float(d.amount) for d in pending_debts)
    total_active = sum(float(d.balance) for d in active_debts)
    total_awaiting = sum(float(d.balance) for d in awaiting_confirmation_debts)
    total_collected = sum(float(d.paid_amount) for d in debts)
    total_debts = debts.count()
    
    # Calculate additional metrics for the template
    total_pending_confirmation = pending_debts.count()
    total_awaiting_confirmation = awaiting_confirmation_debts.count()
    total_remaining_balance = sum(float(d.balance) for d in active_debts) + total_awaiting
    
    # Calculate total debt amount excluding fully paid debts
    total_debt_amount_excluding_paid = sum(float(d.balance) for d in debts.exclude(status='paid'))
    
    # Calculate overall debt total for confirmed/active/awaiting/paid debts only
    total_overall_debt = sum(float(d.amount) for d in debts.exclude(status='pending_confirmation'))
    
    # Group debts by debtor - only include debtors with confirmed/active/paid debts
    debtor_data = []
    debtors_dict = {}
    
    # Only process debts that are not pending or rejected
    confirmed_debts = debts.exclude(status__in=['pending_confirmation', 'rejected'])
    
    for debt in confirmed_debts:
        debtor_id = debt.debtor.id
        if debtor_id not in debtors_dict:
            debtors_dict[debtor_id] = {
                'debtor': debt.debtor,
                'debts': [],
                'total_amount': 0,
                'paid_amount': 0,
                'unpaid_amount': 0,
                'pending_count': 0,
                'active_debts_count': 0,
                'awaiting_count': 0,
                'paid_count': 0,
            }
        
        debtors_dict[debtor_id]['debts'].append(debt)
        debtors_dict[debtor_id]['total_amount'] += float(debt.amount)
        debtors_dict[debtor_id]['paid_amount'] += float(debt.paid_amount)
        debtors_dict[debtor_id]['unpaid_amount'] += float(debt.balance)
        
        if debt.status == 'active':
            debtors_dict[debtor_id]['active_debts_count'] += 1
        elif debt.status == 'awaiting_confirmation':
            debtors_dict[debtor_id]['awaiting_count'] += 1
        elif debt.status == 'paid':
            debtors_dict[debtor_id]['paid_count'] += 1
    
    # Convert debtors_dict to list (debtors with only pending debts are excluded)
    debtor_data = list(debtors_dict.values())
    
    # Count unique debtors with confirmed debts (excluding pending/rejected only)
    total_debtors = len([d for d in debtors_dict.values() if d['active_debts_count'] > 0 or d['paid_count'] > 0])
    
    # Get pending cash payments that need creditor confirmation
    pending_cash_payments = Payment.objects.filter(
        debt__creditor=request.user,
        method='cash',
        status='pending_confirmation'
    ).select_related('debt', 'payer', 'debt__debtor').order_by('-created_at')
    
    # Get pending debt confirmations (debts with status='pending_confirmation')
    pending_confirmations = Debt.objects.filter(
        creditor=request.user,
        status='pending_confirmation'
    ).select_related('debtor').order_by('-date_created')
    
    context = {
        'debtor_data': debtor_data,  # Changed from debtors_summary to debtor_data
        'pending_debts': pending_debts,
        'active_debts': active_debts,
        'awaiting_confirmation_debts': awaiting_confirmation_debts,
        'paid_debts': paid_debts,
        'rejected_debts': rejected_debts,
        'pending_cash_payments': pending_cash_payments,  # NEW: Pending cash payments
        'pending_confirmations': pending_confirmations,  # NEW: Pending debt confirmations
        'total_pending': total_pending,
        'total_active': total_active,
        'total_awaiting': total_awaiting,
        'total_collected': total_collected,
        'total_debts': total_debts,
        'total_debtors': total_debtors,
        'total_pending_confirmation': total_pending_confirmation,
        'total_awaiting_confirmation': total_awaiting_confirmation,
        'total_remaining_balance': total_remaining_balance,
        'total_debt_amount_excluding_paid': total_debt_amount_excluding_paid,
        'total_overall_debt': total_overall_debt,
        'search_query': search_query,
    }
    
    return render(request, 'dashboard_creditor.html', context)


@login_required
def pending_confirmation(request):
    """Dedicated page showing only debts with status='pending_confirmation'."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Access denied. Creditors only.")
        return redirect('myapp:home')
    
    # Get all pending debt confirmations for this creditor
    pending = Debt.objects.filter(
        creditor=request.user,
        status='pending_confirmation'
    ).select_related('debtor').order_by('-date_created')
    
    # Calculate total amount
    total_amount = sum(float(debt.amount) for debt in pending)
    
    context = {
        'pending': pending,
        'total_amount': total_amount,
    }
    
    return render(request, 'creditor_pending_confirmation.html', context)


@login_required
def debtor_dashboard(request):
    if request.user.account_type != 'debtor':
        messages.error(request, "Access denied. Debtors only.")
        return redirect('myapp:home')
    
    # Exclude debts hidden by debtor (soft deleted)
    debts = Debt.objects.filter(debtor=request.user, hidden_from_debtor=False).select_related('creditor')
    
    pending_debts = debts.filter(status='pending_confirmation')
    active_debts = debts.filter(status='active')
    awaiting_confirmation_debts = debts.filter(status='awaiting_confirmation')
    paid_debts = debts.filter(status='paid')
    rejected_debts = debts.filter(status='rejected')
    
    total_pending = sum(float(d.amount) for d in pending_debts)
    total_active = sum(float(d.balance) for d in active_debts)
    total_awaiting = sum(float(d.balance) for d in awaiting_confirmation_debts)
    total_paid = sum(float(d.paid_amount) for d in debts)
    
    creditors_summary = {}
    for debt in debts:
        creditor_id = debt.creditor.id
        if creditor_id not in creditors_summary:
            creditors_summary[creditor_id] = {
                'creditor': debt.creditor,
                'debts': [],
                'total_amount': 0,
                'total_paid': 0,
                'total_balance': 0,
                'pending_count': 0,
                'active_count': 0,
                'awaiting_count': 0,
                'paid_count': 0,
            }
        
        creditors_summary[creditor_id]['debts'].append(debt)
        creditors_summary[creditor_id]['total_amount'] += float(debt.amount)
        creditors_summary[creditor_id]['total_paid'] += float(debt.paid_amount)
        creditors_summary[creditor_id]['total_balance'] += float(debt.balance)
        
        if debt.status == 'pending_confirmation':
            creditors_summary[creditor_id]['pending_count'] += 1
        elif debt.status == 'active':
            creditors_summary[creditor_id]['active_count'] += 1
        elif debt.status == 'awaiting_confirmation':
            creditors_summary[creditor_id]['awaiting_count'] += 1
        elif debt.status == 'paid':
            creditors_summary[creditor_id]['paid_count'] += 1
    
    context = {
        'debts': debts,  # Pass all debts for conditional rendering
        'pending_debts': pending_debts,
        'active_debts': active_debts,
        'awaiting_confirmation_debts': awaiting_confirmation_debts,
        'paid_debts': paid_debts,
        'rejected_debts': rejected_debts,
        'total_pending': total_pending,
        'total_active': total_active,
        'total_awaiting': total_awaiting,
        'total_paid': total_paid,
        'creditors_summary': creditors_summary.values(),
    }
    
    return render(request, 'dashboard_debtor.html', context)


@login_required
def add_debt(request):
    if request.user.account_type != 'debtor':
        messages.error(request, "Only debtors can add debts.")
        return redirect('myapp:home')
    
    if request.method == 'POST':
        form = DebtForm(request.POST, request.FILES)
        if form.is_valid():
            creditor_username = form.cleaned_data['creditor_username']
            try:
                creditor = CustomUser.objects.get(username=creditor_username)
                
                debt = form.save(commit=False)
                debt.debtor = request.user
                debt.creditor = creditor
                debt.status = 'pending_confirmation'
                debt.save()
                
                Notification.objects.create(
                    user=creditor,
                    notification_type='new_debt',
                    message=f'{request.user.full_name} has added a new debt of ₱{debt.amount:.2f}. Please review and confirm.',
                    related_debt=debt
                )
                
                messages.success(request, f'Debt added successfully! Waiting for {creditor.full_name} to confirm.')
                return redirect('myapp:debtor_dashboard')
            except CustomUser.DoesNotExist:
                form.add_error('creditor_username', 'Creditor not found.')
    else:
        form = DebtForm()
    
    return render(request, 'add_debt.html', {'form': form})


@login_required
def add_debtor(request):
    """Add a new debtor (creditor only)."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Only creditors can add debtors.")
        return redirect('myapp:home')
    
    if request.method == 'POST':
        form = AddDebtorForm(request.POST)
        if form.is_valid():
            # This is a placeholder - actual implementation depends on your requirements
            messages.success(request, 'Debtor added successfully!')
            return redirect('myapp:debtor_list')
    else:
        form = AddDebtorForm()
    
    return render(request, 'add_debtor.html', {'form': form})


@login_required
def debtor_list(request):
    """List all debtors (creditor only)."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Only creditors can view debtors.")
        return redirect('myapp:home')
    
    # Get all unique debtors who have debts with this creditor
    debts = Debt.objects.filter(creditor=request.user)
    debtors = CustomUser.objects.filter(
        id__in=debts.values_list('debtor_id', flat=True).distinct(),
        account_type='debtor'
    ).distinct()
    
    context = {
        'debtors': debtors,
    }
    
    return render(request, 'debtor_list.html', context)


@login_required
def edit_debt(request, id):
    debt = get_object_or_404(Debt, id=id)
    
    if debt.debtor != request.user:
        messages.error(request, "You can only edit your own debts.")
        return redirect('myapp:debtor_dashboard')
    
    if debt.status != 'pending_confirmation':
        messages.error(request, "You can only edit debts that are pending confirmation.")
        return redirect('myapp:debtor_dashboard')
    
    if request.method == 'POST':
        form = DebtForm(request.POST, request.FILES, instance=debt)
        if form.is_valid():
            creditor_username = form.cleaned_data['creditor_username']
            try:
                creditor = CustomUser.objects.get(username=creditor_username)
                debt = form.save(commit=False)
                debt.creditor = creditor
                debt.save()
                
                messages.success(request, 'Debt updated successfully!')
                return redirect('myapp:debtor_dashboard')
            except CustomUser.DoesNotExist:
                form.add_error('creditor_username', 'Creditor not found.')
    else:
        form = DebtForm(instance=debt, initial={'creditor_username': debt.creditor.username})
    
    return render(request, 'edit_debt.html', {'form': form, 'debt': debt})


@login_required
def delete_debt(request, id):
    debt = get_object_or_404(Debt, id=id)
    
    if debt.debtor != request.user:
        messages.error(request, "You can only delete your own debts.")
        return redirect('myapp:debtor_dashboard')
    
    # Allow deletion of pending_confirmation, rejected, or paid debts
    if debt.status not in ['pending_confirmation', 'rejected', 'paid']:
        messages.error(request, "You can only delete debts that are pending confirmation, rejected, or fully paid.")
        return redirect('myapp:debtor_dashboard')
    
    if request.method == 'POST':
        debt_status = debt.status
        debt_amount = debt.amount
        
        # For paid debts, use soft delete (hide from debtor only)
        if debt_status == 'paid':
            debt.hidden_from_debtor = True
            debt.save()
            messages.success(request, 'Paid debt removed from your view. Creditor records remain intact.')
        else:
            # For pending/rejected debts, actually delete them
            creditor = debt.creditor
            debt.delete()
            messages.success(request, 'Debt deleted successfully.')
        
        return redirect('myapp:debtor_dashboard')
    
    return redirect('myapp:debtor_dashboard')


@login_required
def creditor_delete_debt(request, id):
    debt = get_object_or_404(Debt, id=id)
    
    if debt.creditor != request.user:
        messages.error(request, "You can only delete debts where you are the creditor.")
        return redirect('myapp:creditor_dashboard')
    
    # Only allow deletion of paid debts
    if debt.status != 'paid':
        messages.error(request, "You can only delete debts that are fully paid.")
        return redirect('myapp:creditor_dashboard')
    
    if request.method == 'POST':
        # For now, use hard delete since hidden_from_creditor field is commented out for production
        # After migration is applied, this will be changed to soft delete
        debtor = debt.debtor
        debt_amount = debt.amount
        debt.delete()
        messages.success(request, 'Paid debt deleted successfully.')
        return redirect('myapp:creditor_dashboard')
    
    return redirect('myapp:creditor_dashboard')


@login_required
def mark_as_paid(request, id):
    """Manually mark a debt as paid (creditor only) with proof upload."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Only creditors can mark debts as paid.")
        return redirect('myapp:home')
    
    debt = get_object_or_404(Debt, id=id)
    
    if debt.creditor != request.user:
        messages.error(request, "You can only mark your own debts as paid.")
        return redirect('myapp:creditor_dashboard')
    
    if request.method == 'POST':
        payment_amount = request.POST.get('payment_amount', debt.balance)
        creditor_proof = request.FILES.get('creditor_proof')
        
        # Validate that proof is uploaded
        if not creditor_proof:
            messages.error(request, 'Proof of receipt is required. Please upload a photo or PDF of the cash receipt.')
            context = {'debt': debt}
            return render(request, 'mark_as_paid.html', context)
        
        try:
            payment_amount = float(payment_amount)
        except (ValueError, TypeError):
            payment_amount = float(debt.balance)
        
        if payment_amount > debt.balance:
            payment_amount = float(debt.balance)
        
        # Update debt
        debt.paid_amount = float(debt.paid_amount) + payment_amount
        
        # Store creditor proof (always required now)
        debt.payment_proof = creditor_proof
        
        if debt.balance <= 0:
            debt.status = 'paid'
            debt.date_paid = timezone.now()
        
        debt.save()
        
        # Create payment record with creditor proof
        payment = Payment.objects.create(
            debt=debt,
            payer=debt.debtor,
            amount=payment_amount,
            method='cash',
            status='completed',
            payment_date=timezone.now(),
            verified_at=timezone.now(),
            creditor_proof=creditor_proof
        )
        
        # Create notifications
        Notification.objects.create(
            user=debt.debtor,
            notification_type='payment_confirmed',
            message=f'{request.user.full_name} has marked your debt of ₱{payment_amount:.2f} as paid.',
            related_debt=debt
        )
        
        messages.success(request, f'Debt marked as paid (₱{payment_amount:.2f}).')
        return redirect('myapp:creditor_dashboard')
    
    context = {
        'debt': debt,
    }
    
    return render(request, 'mark_as_paid.html', context)


@login_required
def send_reminder(request, id):
    """Send payment reminder to debtor (creditor only)."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Only creditors can send reminders.")
        return redirect('myapp:home')
    
    debt = get_object_or_404(Debt, id=id)
    
    if debt.creditor != request.user:
        messages.error(request, "You can only send reminders for your own debts.")
        return redirect('myapp:creditor_dashboard')
    
    if debt.status == 'paid':
        messages.info(request, "This debt is already paid.")
        return redirect('myapp:creditor_dashboard')
    
    # Create reminder notification
    Notification.objects.create(
        user=debt.debtor,
        notification_type='payment_reminder',
        message=f'Reminder: You have an outstanding debt of ₱{debt.balance:.2f} to {request.user.full_name}.',
        related_debt=debt
    )
    
    messages.success(request, f'Payment reminder sent to {debt.debtor.full_name}.')
    return redirect('myapp:creditor_dashboard')


@login_required
def creditor_payments(request):
    """View all payments received (creditor only)."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Only creditors can view payment history.")
        return redirect('myapp:home')
    
    # Exclude rejected payments from creditor history
    payments = Payment.objects.filter(debt__creditor=request.user).exclude(status='rejected').select_related('debt', 'payer', 'debt__debtor', 'debt__creditor').order_by('-payment_date', '-created_at')
    
    total_received = sum(float(p.amount) for p in payments)
    payment_count = payments.count()
    average_payment = total_received / payment_count if payment_count > 0 else 0
    
    context = {
        'payments': payments,
        'total_received': total_received,
        'payment_count': payment_count,
        'average_payment': average_payment,
    }
    
    return render(request, 'creditor_payments.html', context)


@login_required
def all_debts_view(request):
    """View all debts grouped by debtor (creditor only)."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Only creditors can view all debts.")
        return redirect('myapp:home')
    
    debts = Debt.objects.filter(creditor=request.user).select_related('debtor').order_by('debtor__full_name', '-date_created')
    
    # Group by debtor
    debtors_dict = {}
    for debt in debts:
        debtor_id = debt.debtor.id
        if debtor_id not in debtors_dict:
            debtors_dict[debtor_id] = {
                'debtor': debt.debtor,
                'debts': [],
                'total_amount': 0,
                'total_paid': 0,
                'total_balance': 0,
            }
        
        debtors_dict[debtor_id]['debts'].append(debt)
        debtors_dict[debtor_id]['total_amount'] += float(debt.amount)
        debtors_dict[debtor_id]['total_paid'] += float(debt.paid_amount)
        debtors_dict[debtor_id]['total_balance'] += float(debt.balance)
    
    context = {
        'debtors_data': debtors_dict.values(),
    }
    
    return render(request, 'all_debts.html', context)


@login_required
def confirm_debt(request, id):
    debt = get_object_or_404(Debt, id=id)
    
    if debt.creditor != request.user:
        messages.error(request, "You can only confirm debts where you are the creditor.")
        return redirect('myapp:creditor_dashboard')
    
    if debt.status != 'pending_confirmation':
        messages.error(request, "This debt is not pending confirmation.")
        return redirect('myapp:creditor_dashboard')
    
    if request.method == 'POST':
        debt.status = 'active'
        debt.save()
        
        Notification.objects.create(
            user=debt.debtor,
            notification_type='debt_confirmed',
            message=f'{request.user.full_name} has confirmed your debt of ₱{debt.amount:.2f}. The debt is now active.',
            related_debt=debt
        )
        
        messages.success(request, f'Debt confirmed! {debt.debtor.full_name} now owes you ₱{debt.amount:.2f}.')
        return redirect('myapp:creditor_dashboard')
    
    return render(request, 'confirm_debt.html', {'debt': debt})


@login_required
def upload_proof_of_release(request, id):
    debt = get_object_or_404(Debt, id=id)
    
    if debt.creditor != request.user:
        messages.error(request, "You can only upload proof for debts where you are the creditor.")
        return redirect('myapp:creditor_dashboard')
    
    if debt.status != 'pending_confirmation' and debt.status != 'active':
        messages.error(request, "Cannot upload proof for this debt.")
        return redirect('myapp:creditor_dashboard')
    
    if request.method == 'POST':
        proof_file = request.FILES.get('creditor_proof')
        if proof_file:
            debt.creditor_proof = proof_file
            if debt.status == 'pending_confirmation':
                debt.status = 'active'
            debt.save()
            
            Notification.objects.create(
                user=debt.debtor,
                notification_type='proof_uploaded',
                message=f'{request.user.full_name} has uploaded proof of release for the debt of ₱{debt.amount:.2f}.',
                related_debt=debt
            )
            
            messages.success(request, 'Proof of release uploaded successfully!')
        else:
            messages.error(request, 'Please select a file to upload.')
        
        return redirect('myapp:creditor_dashboard')
    
    return render(request, 'upload_proof_of_release.html', {'debt': debt})


@login_required
def reject_debt(request, id):
    debt = get_object_or_404(Debt, id=id)
    
    if debt.creditor != request.user:
        messages.error(request, "You can only reject debts where you are the creditor.")
        return redirect('myapp:creditor_dashboard')
    
    if debt.status != 'pending_confirmation':
        messages.error(request, "This debt is not pending confirmation.")
        return redirect('myapp:creditor_dashboard')
    
    if request.method == 'POST':
        debt.status = 'rejected'
        debt.save()
        
        Notification.objects.create(
            user=debt.debtor,
            notification_type='debt_rejected',
            message=f'{request.user.full_name} has rejected your debt submission of ₱{debt.amount:.2f}.',
            related_debt=debt
        )
        
        messages.success(request, 'Debt rejected.')
        return redirect('myapp:creditor_dashboard')
    
    return redirect('myapp:creditor_dashboard')


@login_required
def pay_debt(request, id):
    """Show payment method selection for a debt."""
    if request.user.account_type != 'debtor':
        messages.error(request, "Only debtors can make payments.")
        return redirect('myapp:home')
    
    debt = get_object_or_404(Debt, id=id)
    
    if debt.debtor != request.user:
        messages.error(request, "You can only pay your own debts.")
        return redirect('myapp:debtor_dashboard')
    
    if debt.status not in ['active', 'pending_confirmation']:
        messages.error(request, "This debt cannot be paid.")
        return redirect('myapp:debtor_dashboard')
    
    remaining_balance = debt.balance
    
    if remaining_balance <= 0:
        messages.info(request, "This debt is already fully paid.")
        return redirect('myapp:debtor_dashboard')
    
    context = {
        'debt': debt,
        'remaining_balance': remaining_balance,
    }
    
    return render(request, 'payment_method.html', context)


@login_required
def submit_payment(request, id):
    """Process payment method selection and redirect to payment gateway."""
    if request.user.account_type != 'debtor':
        messages.error(request, "Only debtors can make payments.")
        return redirect('myapp:home')
    
    debt = get_object_or_404(Debt, id=id)
    
    if debt.debtor != request.user:
        messages.error(request, "You can only pay your own debts.")
        return redirect('myapp:debtor_dashboard')
    
    if request.method == 'POST':
        method = request.POST.get('method', '').strip()
        payment_amount = request.POST.get('amount', '0')
        
        try:
            payment_amount = float(payment_amount)
        except (ValueError, TypeError):
            messages.error(request, "Invalid payment amount.")
            return redirect('myapp:pay_debt', id=id)
        
        remaining_balance = debt.balance
        
        if payment_amount <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect('myapp:pay_debt', id=id)
        
        if payment_amount > remaining_balance:
            messages.error(request, f"Payment amount cannot exceed remaining balance (₱{remaining_balance:.2f}).")
            return redirect('myapp:pay_debt', id=id)
        
        # Store payment info in session
        request.session['payment_debt_id'] = debt.id
        request.session['payment_amount'] = payment_amount
        request.session['payment_method'] = method
        
        # Redirect based on payment method
        if method == 'cash':
            return redirect('myapp:upload_debtor_proof', payment_id=0)
        elif method == 'gcash':
            return redirect('myapp:gcash_payment')
        else:
            messages.error(request, "Invalid payment method selected.")
    
    return redirect('myapp:pay_debt', id=id)


@login_required
def gcash_payment(request):
    """Mock GCash payment gateway."""
    if request.user.account_type != 'debtor':
        return redirect('myapp:creditor_dashboard')
    
    debt_id = request.session.get('payment_debt_id')
    if not debt_id:
        messages.error(request, "No payment session found. Please start a new payment.")
        return redirect('myapp:debtor_dashboard')
    
    debt = get_object_or_404(Debt, id=debt_id)
    
    if debt.debtor != request.user:
        messages.error(request, "Access denied.")
        return redirect('myapp:debtor_dashboard')
    
    if request.method == 'POST':
        # Process payment
        payment_amount = request.session.get('payment_amount', debt.balance)
        
        # Create payment record
        payment = Payment.objects.create(
            debt=debt,
            payer=request.user,
            amount=payment_amount,
            method='gcash',
            status='completed',
            payment_date=timezone.now(),
            verified_at=timezone.now()
        )
        
        # Update debt
        debt.paid_amount = float(debt.paid_amount) + payment_amount
        if debt.balance <= 0:
            debt.status = 'paid'
            debt.date_paid = timezone.now()
        debt.save()
        
        # Generate PDF receipt
        if REPORTLAB_AVAILABLE:
            pdf_file = generate_pdf_receipt(payment)
            payment.receipt_file.save(f'receipt_{payment.receipt_no}.pdf', ContentFile(pdf_file.getvalue()))
            payment.save()
        
        # Clear session
        if 'payment_debt_id' in request.session:
            del request.session['payment_debt_id']
        if 'payment_amount' in request.session:
            del request.session['payment_amount']
        if 'payment_method' in request.session:
            del request.session['payment_method']
        
        # Create notifications
        Notification.objects.create(
            user=request.user,
            notification_type='payment_success',
            message=f'Your payment of ₱{payment_amount:.2f} via GCash was successful!',
            related_debt=debt
        )
        
        Notification.objects.create(
            user=debt.creditor,
            notification_type='payment_received',
            message=f'{request.user.full_name} has paid ₱{payment_amount:.2f} via GCash.',
            related_debt=debt
        )
        
        messages.success(request, f'Payment of ₱{payment_amount:.2f} processed successfully!')
        return redirect('myapp:payment_success', payment_id=payment.id)
    
    context = {
        'debt': debt,
    }
    
    return render(request, 'mock_gcash_payment.html', context)


@login_required
def payment_success(request, payment_id):
    """Display payment success page."""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if payment.payer != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if payment.debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    else:
        messages.error(request, "Access denied.")
        return redirect('myapp:home')
    
    context = {
        'payment': payment,
        'debt': payment.debt,
    }
    
    return render(request, 'payment_success.html', context)


def generate_pdf_receipt(payment):
    """Generate PDF receipt for a payment."""
    if not REPORTLAB_AVAILABLE:
        return None
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#013A63'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    elements.append(Paragraph("PAYMENT RECEIPT", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Receipt Number
    receipt_style = ParagraphStyle(
        'ReceiptNumber',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph(f"Receipt No: {payment.receipt_no}", receipt_style))
    elements.append(Paragraph(f"Transaction ID: {payment.transaction_id}", receipt_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Payment Details
    data = [
        ['Payment Date', payment.payment_date.strftime('%B %d, %Y %I:%M %p') if payment.payment_date else 'N/A'],
        ['Payment Method', payment.get_method_display().upper()],
        ['Amount Paid', f'₱{payment.amount:.2f}'],
        ['Debtor', payment.debt.debtor.full_name],
        ['Creditor', payment.debt.creditor.full_name],
        ['Status', 'PAID'],
    ]
    
    table = Table(data, colWidths=[2*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, -1), (1, -1), colors.HexColor('#28a745')),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.whitesmoke),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph("This is a computer-generated receipt.", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


@login_required
def view_receipt(request, id):
    """View payment receipt."""
    payment = get_object_or_404(Payment, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if payment.payer != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if payment.debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    else:
        messages.error(request, "Access denied.")
        return redirect('myapp:home')
    
    context = {
        'payment': payment,
        'debt': payment.debt,
    }
    
    return render(request, 'receipt.html', context)


@login_required
def download_receipt_pdf(request, payment_id):
    """Download PDF receipt for a payment."""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if payment.payer != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if payment.debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    
    if payment.receipt_file and payment.receipt_file.name:
        return FileResponse(open(payment.receipt_file.path, 'rb'), as_attachment=True, filename=f'receipt_{payment.receipt_no}.pdf')
    else:
        messages.error(request, "Receipt file not found.")
        return redirect('myapp:payment_success', payment_id=payment.id)


@login_required
def upload_debtor_proof(request, payment_id):
    """Upload proof of payment for cash payments."""
    if request.user.account_type != 'debtor':
        messages.error(request, "Only debtors can upload payment proof.")
        return redirect('myapp:home')
    
    # Get debt information from session
    debt_id = request.session.get('payment_debt_id')
    payment_amount = request.session.get('payment_amount', 0)
    
    if not debt_id:
        messages.error(request, "No payment session found. Please start a new payment.")
        return redirect('myapp:debtor_dashboard')
    
    debt = get_object_or_404(Debt, id=debt_id)
    
    if debt.debtor != request.user:
        messages.error(request, "Access denied.")
        return redirect('myapp:debtor_dashboard')
    
    if request.method == 'POST':
        proof_file = request.FILES.get('proof')
        
        if not proof_file:
            messages.error(request, "Please upload a proof of payment.")
            return render(request, 'upload_debtor_proof.html', {
                'debt': debt,
                'payment_amount': payment_amount,
            })
        
        # Create payment record
        payment = Payment.objects.create(
            debt=debt,
            payer=request.user,
            amount=payment_amount,
            method='cash',
            status='pending_confirmation',  # Changed from pending_creditor_proof
            debtor_proof=proof_file
        )
        
        # Update debt - mark as awaiting confirmation (don't update paid_amount yet)
        # Payment will be confirmed by creditor first
        debt.status = 'awaiting_confirmation'
        debt.save()
        
        # Clear session
        if 'payment_debt_id' in request.session:
            del request.session['payment_debt_id']
        if 'payment_amount' in request.session:
            del request.session['payment_amount']
        if 'payment_method' in request.session:
            del request.session['payment_method']
        
        # Create notifications
        Notification.objects.create(
            user=request.user,
            notification_type='payment_submitted',
            message=f'Your payment proof of ₱{payment_amount:.2f} has been uploaded. Waiting for creditor confirmation.',
            related_debt=debt
        )
        
        Notification.objects.create(
            user=debt.creditor,
            notification_type='payment_proof_received',
            message=f'{request.user.full_name} has uploaded proof of cash payment (₱{payment_amount:.2f}). Please review and confirm.',
            related_debt=debt
        )
        
        messages.success(request, 'Payment proof uploaded! Waiting for creditor confirmation.')
        return redirect('myapp:payment_success', payment_id=payment.id)
    
    # GET request - show upload form
    context = {
        'debt': debt,
        'payment_amount': payment_amount,
        'creditor': debt.creditor,
        'payment_method': 'Cash',
    }
    
    return render(request, 'upload_debtor_proof.html', context)


@login_required
def confirm_cash_payment(request, payment_id):
    """Creditor confirms or rejects cash payment proof uploaded by debtor."""
    if request.user.account_type != 'creditor':
        messages.error(request, "Only creditors can confirm payments.")
        return redirect('myapp:home')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if payment.debt.creditor != request.user:
        messages.error(request, "You can only confirm payments for your debts.")
        return redirect('myapp:creditor_dashboard')
    
    if payment.status != 'pending_confirmation':
        messages.error(request, "This payment has already been processed.")
        return redirect('myapp:creditor_dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm':
            # Confirm the payment
            payment.status = 'completed'
            payment.verified_at = timezone.now()
            payment.payment_date = timezone.now()
            payment.save()
            
            # Update debt - add payment to paid_amount
            debt = payment.debt
            debt.paid_amount = float(debt.paid_amount) + float(payment.amount)
            
            # Check if fully paid
            if debt.balance <= 0:
                debt.status = 'paid'
                debt.date_paid = timezone.now()
            else:
                debt.status = 'active'  # Return to active if partially paid
            debt.save()
            
            # Generate PDF receipt
            if REPORTLAB_AVAILABLE:
                pdf_file = generate_pdf_receipt(payment)
                payment.receipt_file.save(f'receipt_{payment.receipt_no}.pdf', ContentFile(pdf_file.getvalue()))
                payment.save()
            
            # Create notifications
            Notification.objects.create(
                user=payment.payer,
                notification_type='payment_confirmed',
                message=f'Your cash payment of ₱{payment.amount:.2f} has been confirmed by {request.user.full_name}!',
                related_debt=payment.debt
            )
            
            messages.success(request, f'Payment of ₱{payment.amount:.2f} confirmed successfully!')
            
        elif action == 'reject':
            # Reject the payment
            payment.status = 'rejected'
            payment.save()
            
            # Return debt to active status
            debt = payment.debt
            debt.status = 'active'
            debt.save()
            
            # Create notification
            Notification.objects.create(
                user=payment.payer,
                notification_type='payment_rejected',
                message=f'Your payment proof of ₱{payment.amount:.2f} was rejected. Please contact {request.user.full_name} for clarification.',
                related_debt=payment.debt
            )
            
            messages.warning(request, 'Payment proof rejected.')
        
        return redirect('myapp:creditor_dashboard')
    
    context = {
        'payment': payment,
        'debt': payment.debt,
    }
    
    return render(request, 'confirm_cash_payment.html', context)


@login_required
def transaction_history(request):
    """View transaction history."""
    # Base queryset: hide rejected payments from user-facing history
    payments = Payment.objects.exclude(status='rejected')
    
    if request.user.account_type == 'debtor':
        payments = payments.filter(payer=request.user)
    elif request.user.account_type == 'creditor':
        payments = payments.filter(debt__creditor=request.user)
    
    # Filter by payment method
    method_filter = request.GET.get('method', '').strip()
    if method_filter:
        payments = payments.filter(method=method_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            payments = payments.filter(payment_date__gte=date_from_obj.date())
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            payments = payments.filter(payment_date__lte=date_to_obj.date())
        except ValueError:
            pass
    
    payments = payments.order_by('-payment_date', '-created_at')
    
    total_amount = sum(float(p.amount) for p in payments)
    
    context = {
        'payments': payments,
        'total_amount': total_amount,
        'total_count': payments.count(),
        'method_filter': method_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'transaction_history.html', context)


@login_required
def notifications_view(request):
    """View all notifications."""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    messages.success(request, 'Notification marked as read.')
    return redirect('myapp:notifications')


@login_required
def delete_notification(request, notification_id):
    """Delete a notification."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    
    messages.success(request, 'Notification deleted.')
    return redirect('myapp:notifications')


@login_required
def mark_all_read(request):
    """Mark all notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    messages.success(request, 'All notifications marked as read.')
    return redirect('myapp:notifications')


@login_required
def clear_all_notifications(request):
    """Delete all notifications."""
    Notification.objects.filter(user=request.user).delete()
    
    messages.success(request, 'All notifications cleared.')
    return redirect('myapp:notifications')


@login_required
def debt_detail(request, id):
    """View detailed information about a debt."""
    debt = get_object_or_404(Debt, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if debt.debtor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    else:
        messages.error(request, "Access denied.")
        return redirect('myapp:home')
    
    # Get all completed payments for this debt (pending cash payments are NOT counted yet)
    payments = Payment.objects.filter(debt=debt, status='completed').order_by('payment_date', 'created_at')
    
    # Get all payments (including pending) for proof display
    all_payments = Payment.objects.filter(debt=debt).order_by('-created_at')
    
    # Determine primary payment method (most recent non-rejected payment)
    primary_payment = all_payments.exclude(status='rejected').first()
    primary_payment_method = primary_payment.method if primary_payment else None
    
    # Get the most recent GCash payment (for receipt display)
    latest_gcash_payment = all_payments.filter(method='gcash', status='completed').first()
    
    # Get the most recent Cash payment (for proof display)
    latest_cash_payment = all_payments.filter(method='cash').exclude(status='rejected').first()
    
    # Calculate running balance for each payment
    payments_with_balance = []
    running_paid = 0
    
    for payment in payments:
        running_paid += float(payment.amount)
        balance_after = float(debt.amount) - running_paid
        
        payments_with_balance.append({
            'payment': payment,
            'running_paid': running_paid,
            'balance_after': max(0, balance_after),
            'is_full_payment': balance_after <= 0
        })
    
    # Determine where the user came from (dashboard vs notifications) for back button text
    from_page = request.GET.get('from', None)

    context = {
        'debt': debt,
        'payments': payments,
        'payments_with_balance': payments_with_balance,
        'primary_payment_method': primary_payment_method,
        'latest_gcash_payment': latest_gcash_payment,
        'latest_cash_payment': latest_cash_payment,
        'total_paid': running_paid,
        'remaining_balance': debt.balance,
        'last_payment': payments.first() if payments.exists() else None,
        'last_payment_date': payments.first().payment_date if payments.exists() else None,
        'from_page': from_page,
    }
    
    return render(request, 'debt_detail.html', context)


@login_required
def user_profile(request):
    """View user profile with statistics."""
    user = request.user
    
    # Initialize statistics dictionary
    stats = {}
    
    if user.account_type == 'debtor':
        # Debtor statistics
        debts = Debt.objects.filter(debtor=user)
        
        # Total creditors (distinct)
        stats['total_creditors'] = debts.values('creditor').distinct().count()
        
        # Total debts
        stats['total_debts'] = debts.count()
        
        # Paid debts (status = 'paid')
        stats['paid_debts'] = debts.filter(status='paid').count()
        
        # Unpaid debts (status != 'paid')
        stats['unpaid_debts'] = debts.exclude(status='paid').count()
        
        # Total amount owed (sum of balances for unpaid debts)
        unpaid_debts = debts.exclude(status='paid')
        stats['total_amount_owed'] = sum(float(debt.balance) for debt in unpaid_debts)
        
    else:
        # Creditor statistics
        debts = Debt.objects.filter(creditor=user)
        
        # Total debtors (distinct)
        stats['total_debtors'] = debts.values('debtor').distinct().count()
        
        # Total debts
        stats['total_debts'] = debts.count()
        
        # Paid debts (status = 'paid')
        stats['paid_debts'] = debts.filter(status='paid').count()
        
        # Unpaid debts (status != 'paid')
        stats['unpaid_debts'] = debts.exclude(status='paid').count()
        
        # Total unpaid amount (sum of balances for unpaid debts)
        unpaid_debts = debts.exclude(status='paid')
        stats['total_amount_owed'] = sum(float(debt.balance) for debt in unpaid_debts)
    
    context = {
        'user': user,
        'stats': stats,
    }
    
    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile with AJAX support."""
    if request.method == 'POST':
        user = request.user
        errors = []
        
        # Get form data
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        profile_picture = request.FILES.get('profile_picture')
        
        # Password change fields
        old_password = request.POST.get('old_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        # Validate and update basic info
        if full_name:
            user.full_name = full_name
        else:
            errors.append('Full name is required.')
        
        # Update email (can be empty)
        user.email = email if email else ''
        
        # Handle profile picture upload
        if profile_picture:
            # Validate file size (5MB max)
            if profile_picture.size > 5 * 1024 * 1024:
                errors.append('Profile picture must be less than 5MB.')
            else:
                # Validate file type (only jpg, jpeg, png)
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
                if profile_picture.content_type not in allowed_types:
                    errors.append('Profile picture must be JPG, JPEG, or PNG only.')
                else:
                    # Delete old profile picture if exists
                    if user.profile_picture:
                        try:
                            user.profile_picture.delete(save=False)
                        except:
                            pass
                    user.profile_picture = profile_picture
        
        # Handle password change (optional - only if user filled in at least one password field)
        password_changed = False
        # Check if any password field has actual content (not just whitespace)
        has_password_input = bool(old_password) or bool(new_password) or bool(confirm_password)
        
        if has_password_input:
            # User wants to change password, validate all fields
            if not old_password:
                errors.append('Current password is required to change password.')
            elif not user.check_password(old_password):
                errors.append('Current password is incorrect.')
            elif not new_password:
                errors.append('New password is required to change password.')
            elif len(new_password) < 8:
                errors.append('New password must be at least 8 characters long.')
            elif not confirm_password:
                errors.append('Please confirm your new password.')
            elif new_password != confirm_password:
                errors.append('New passwords do not match.')
            else:
                user.set_password(new_password)
                password_changed = True
        
        # Save if no errors
        if not errors:
            user.save()
            
            # If password was changed, re-authenticate the user
            if password_changed:
                # Update session to prevent logout
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, 'Profile and password updated successfully!')
            else:
                messages.success(request, 'Profile updated successfully!')
            
            # Check if AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({
                    'success': True,
                    'message': 'Profile updated successfully!',
                    'profile_picture_url': user.profile_picture.url if user.profile_picture else None
                })
            
            return redirect('myapp:profile')
        else:
            # Return errors
            for error in errors:
                messages.error(request, error)
            
            # Check if AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'errors': errors
                }, status=400)
            
            return redirect('myapp:profile')
    
    context = {
        'user': request.user,
    }
    
    return render(request, 'edit_profile.html', context)


@login_required
def change_password(request):
    """Change user password."""
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not all([old_password, new_password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return redirect('myapp:change_password')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('myapp:change_password')
        
        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('myapp:change_password')
        
        request.user.set_password(new_password)
        request.user.save()
        
        messages.success(request, 'Password changed successfully! Please login again.')
        return redirect('myapp:login')
    
    return render(request, 'change_password.html')


@login_required
def download_debt_proof(request, id):
    """Download debt proof file."""
    debt = get_object_or_404(Debt, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if debt.debtor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    
    if debt.debt_proof and debt.debt_proof.name:
        return FileResponse(open(debt.debt_proof.path, 'rb'), as_attachment=True)
    else:
        messages.error(request, "Proof file not found.")
        return redirect('myapp:debt_detail', id=id)


def download_creditor_proof(request, id):
    """Download creditor proof file."""
    debt = get_object_or_404(Debt, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if debt.debtor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    
    if debt.creditor_proof and debt.creditor_proof.name:
        return FileResponse(open(debt.creditor_proof.path, 'rb'), as_attachment=True)
    else:
        messages.error(request, "Proof file not found.")
        return redirect('myapp:debt_detail', id=id)


@login_required
def download_payment_proof(request, id):
    """Download payment proof file."""
    payment = get_object_or_404(Payment, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if payment.payer != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if payment.debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    
    if payment.debtor_proof and payment.debtor_proof.name:
        return FileResponse(open(payment.debtor_proof.path, 'rb'), as_attachment=True)
    elif payment.creditor_proof and payment.creditor_proof.name:
        return FileResponse(open(payment.creditor_proof.path, 'rb'), as_attachment=True)
    else:
        messages.error(request, "Proof file not found.")
        return redirect('myapp:payment_success', payment_id=payment.id)


@login_required
def view_debt_proof(request, id):
    """View debt proof file inline."""
    debt = get_object_or_404(Debt, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if debt.debtor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    
    if debt.debt_proof and debt.debt_proof.name:
        return FileResponse(open(debt.debt_proof.path, 'rb'))
    else:
        messages.error(request, "Proof file not found.")
        return redirect('myapp:debt_detail', id=id)


@login_required
def view_creditor_proof(request, id):
    """View creditor proof file inline."""
    debt = get_object_or_404(Debt, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if debt.debtor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    
    if debt.creditor_proof and debt.creditor_proof.name:
        return FileResponse(open(debt.creditor_proof.path, 'rb'))
    else:
        messages.error(request, "Proof file not found.")
        return redirect('myapp:debt_detail', id=id)


@login_required
def view_payment_proof(request, id):
    """View payment proof file inline."""
    payment = get_object_or_404(Payment, id=id)
    
    # Verify access
    if request.user.account_type == 'debtor':
        if payment.payer != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:debtor_dashboard')
    elif request.user.account_type == 'creditor':
        if payment.debt.creditor != request.user:
            messages.error(request, "Access denied.")
            return redirect('myapp:creditor_dashboard')
    
    if payment.debtor_proof and payment.debtor_proof.name:
        return FileResponse(open(payment.debtor_proof.path, 'rb'))
    elif payment.creditor_proof and payment.creditor_proof.name:
        return FileResponse(open(payment.creditor_proof.path, 'rb'))
    else:
        messages.error(request, "Proof file not found.")
        return redirect('myapp:payment_success', payment_id=payment.id)


# ========================================
# ADMIN DASHBOARD VIEWS
# ========================================
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from datetime import datetime, timedelta


def is_superuser(user):
    """Check if user is superuser."""
    return user.is_superuser


@user_passes_test(is_superuser)
def admin_creditors(request):
    """Admin view to list all creditors."""
    from .models import CustomUser, AdminActivityLog
    
    creditors = CustomUser.objects.filter(account_type='creditor').order_by('-date_joined')
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_users',
        description='Viewed creditors list'
    )
    
    context = {
        'creditors': creditors,
        'total_creditors': creditors.count(),
    }
    return render(request, 'admin/admin_creditors.html', context)


@user_passes_test(is_superuser)
def admin_debtors(request):
    """Admin view to list all debtors."""
    from .models import CustomUser, AdminActivityLog
    
    debtors = CustomUser.objects.filter(account_type='debtor').order_by('-date_joined')
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_users',
        description='Viewed debtors list'
    )
    
    context = {
        'debtors': debtors,
        'total_debtors': debtors.count(),
    }
    return render(request, 'admin/admin_debtors.html', context)


@user_passes_test(is_superuser)
def admin_pending_confirmations(request):
    """Admin view to list all pending confirmations."""
    from .models import Debt, AdminActivityLog
    
    pending_debts = Debt.objects.filter(status='pending_confirmation').select_related('creditor', 'debtor').order_by('-date_created')
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_debts',
        description='Viewed pending confirmations'
    )
    
    context = {
        'pending_debts': pending_debts,
        'total_pending': pending_debts.count(),
    }
    return render(request, 'admin/admin_pending_confirmations.html', context)


@user_passes_test(is_superuser)
def admin_activity_logs(request):
    """Admin view to show activity logs."""
    from .models import AdminActivityLog
    
    activities = AdminActivityLog.objects.select_related('user').order_by('-timestamp')
    
    context = {
        'activities': activities,
        'total_activities': activities.count(),
    }
    return render(request, 'admin/admin_activity_logs.html', context)


@user_passes_test(is_superuser)
def admin_settings(request):
    """Admin settings page."""
    from .models import AdminActivityLog
    
    if request.method == 'POST':
        # Handle settings update here
        AdminActivityLog.objects.create(
            user=request.user,
            action='update_settings',
            description='Updated admin settings'
        )
        messages.success(request, 'Settings updated successfully!')
        return redirect('myapp:admin_settings')
    
    context = {
        'settings': {
            'site_name': 'Debt Tracker',
            'admin_email': 'admin@debttracker.com',
            'maintenance_mode': False,
            'allow_registration': True,
        }
    }
    return render(request, 'admin/admin_settings.html', context)


@user_passes_test(is_superuser)
def admin_dashboard(request):
    """Custom admin dashboard with comprehensive system statistics."""
    import json
    from .models import CustomUser, Debt, Payment
    
    # Get statistics
    total_users = CustomUser.objects.count()
    total_creditors = CustomUser.objects.filter(account_type='creditor').count()
    total_debtors = CustomUser.objects.filter(account_type='debtor').count()
    
    # Calculate financial statistics
    total_amount_borrowed = Debt.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_amount_paid = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
    
    # Get timeframe and date filters from request
    timeframe = request.GET.get('timeframe', 'monthly')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    # Parse dates
    today = datetime.now().date()
    if timeframe == 'daily':
        days_back = 30
    elif timeframe == 'yearly':
        days_back = 365
    else:  # monthly
        days_back = 90
    
    start_date = today - timedelta(days=days_back)
    end_date = today
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except:
            pass
    
    # Generate chart data based on timeframe
    chart_labels = []
    creditors_data = []
    debtors_data = []
    
    if timeframe == 'daily':
        # Daily data for the selected range
        current = start_date
        while current <= end_date:
            chart_labels.append(current.strftime('%Y-%m-%d'))
            creditors_count = CustomUser.objects.filter(
                account_type='creditor',
                date_joined__date__lte=current
            ).count()
            debtors_count = CustomUser.objects.filter(
                account_type='debtor',
                date_joined__date__lte=current
            ).count()
            creditors_data.append(creditors_count)
            debtors_data.append(debtors_count)
            current += timedelta(days=1)
    
    elif timeframe == 'monthly':
        # Monthly data
        current = start_date.replace(day=1)
        while current <= end_date:
            month_label = current.strftime('%B %Y')
            chart_labels.append(month_label)
            
            # Count creditors and debtors created up to this month
            month_end = (current.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            creditors_count = CustomUser.objects.filter(
                account_type='creditor',
                date_joined__date__lte=month_end
            ).count()
            debtors_count = CustomUser.objects.filter(
                account_type='debtor',
                date_joined__date__lte=month_end
            ).count()
            creditors_data.append(creditors_count)
            debtors_data.append(debtors_count)
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    
    else:  # yearly
        # Yearly data
        current_year = start_date.year
        end_year = end_date.year
        while current_year <= end_year:
            chart_labels.append(str(current_year))
            year_end = datetime(current_year, 12, 31).date()
            creditors_count = CustomUser.objects.filter(
                account_type='creditor',
                date_joined__date__lte=year_end
            ).count()
            debtors_count = CustomUser.objects.filter(
                account_type='debtor',
                date_joined__date__lte=year_end
            ).count()
            creditors_data.append(creditors_count)
            debtors_data.append(debtors_count)
            current_year += 1
    
    context = {
        'total_users': total_users,
        'total_creditors': total_creditors,
        'total_debtors': total_debtors,
        'total_amount_borrowed': total_amount_borrowed,
        'total_amount_paid': total_amount_paid,
        'chart_labels': json.dumps(chart_labels),
        'creditors_data': json.dumps(creditors_data),
        'debtors_data': json.dumps(debtors_data),
    }
    return render(request, 'admin/dashboard.html', context)


@user_passes_test(is_superuser)
def admin_users(request):
    """Admin view to list all creditors and debtors."""
    from .models import CustomUser, Debt, Payment, AdminActivityLog
    
    # Get creditors and debtors
    creditors = CustomUser.objects.filter(account_type='creditor').order_by('-date_joined')
    debtors = CustomUser.objects.filter(account_type='debtor').order_by('-date_joined')
    
    # Calculate total loaned for each creditor and attach to object
    for creditor in creditors:
        total_loaned = Debt.objects.filter(creditor=creditor).aggregate(total=Sum('amount'))['total'] or 0
        creditor.total_loaned = total_loaned
    
    # Calculate total owed for each debtor and attach to object
    for debtor in debtors:
        total_owed = Debt.objects.filter(debtor=debtor).aggregate(total=Sum('amount'))['total'] or 0
        debtor.total_owed = total_owed
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_users',
        description=f'Admin {request.user.username} viewed users list',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
    
    context = {
        'creditors': creditors,
        'debtors': debtors,
    }
    
    return render(request, 'admin/users.html', context)


@user_passes_test(is_superuser)
def admin_user_detail(request, user_id):
    """Admin view to see user details."""
    from .models import CustomUser, Debt, Payment, AdminActivityLog
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Get user's debts and payments
    if user.account_type == 'creditor':
        debts = Debt.objects.filter(creditor=user).order_by('-date_created')
    else:
        debts = Debt.objects.filter(debtor=user).order_by('-date_created')
    
    payments = Payment.objects.filter(payer=user).order_by('-created_at')
    
    # Compute financial summaries
    total_amount = sum(float(d.amount) for d in debts)
    total_paid = sum(float(d.paid_amount) for d in debts)
    total_balance = sum(float(d.balance) for d in debts)
    paid_debts_count = debts.filter(status='paid').count()
    
    # Map to context keys expected by template
    if user.account_type == 'creditor':
        total_loaned = total_amount
        total_owed = 0
    else:
        total_loaned = 0
        total_owed = total_amount
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_user_detail',
        description=f'Admin {request.user.username} viewed details for user {user.username}',
        related_id=user.id,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
    
    context = {
        'target_user': user,
        'debts': debts,
        'payments': payments,
        'total_loaned': total_loaned,
        'total_owed': total_owed,
        'total_balance': total_balance,
        'paid_debts_count': paid_debts_count,
        'total_paid': total_paid,
    }
    
    return render(request, 'admin/user_detail.html', context)


@user_passes_test(is_superuser)
def admin_debts(request):
    """Admin view to list all debts."""
    from .models import Debt, AdminActivityLog
    
    debts = Debt.objects.select_related('creditor', 'debtor').order_by('-date_created')
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_debts',
        description=f'Admin {request.user.username} viewed debts list',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
    
    context = {
        'debts': debts,
    }
    
    return render(request, 'admin/debts.html', context)


@user_passes_test(is_superuser)
def admin_debt_detail(request, debt_id):
    """Admin view to see debt details with full proof context."""
    from .models import Debt, Payment, AdminActivityLog

    debt = get_object_or_404(Debt, id=debt_id)

    # Completed payments for this debt (same logic as debtor/creditor detail)
    payments = Payment.objects.filter(debt=debt, status='completed').order_by('payment_date', 'created_at')

    # All payments (including pending) for proof display
    all_payments = Payment.objects.filter(debt=debt).order_by('-created_at')

    # Determine primary payment method (most recent non-rejected payment)
    primary_payment = all_payments.exclude(status='rejected').first()
    primary_payment_method = primary_payment.method if primary_payment else None

    # Most recent GCash payment (for receipt display)
    latest_gcash_payment = all_payments.filter(method='gcash', status='completed').first()

    # Most recent Cash payment (for proof display)
    latest_cash_payment = all_payments.filter(method='cash').exclude(status='rejected').first()

    # Calculate running balance per payment (for admin insight)
    payments_with_balance = []
    running_paid = 0
    for payment in payments:
        running_paid += float(payment.amount)
        balance_after = float(debt.amount) - running_paid
        payments_with_balance.append({
            'payment': payment,
            'running_paid': running_paid,
            'balance_after': max(0, balance_after),
            'is_full_payment': balance_after <= 0,
        })

    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_debt_detail',
        description=f'Admin {request.user.username} viewed details for debt #{debt.id}',
        related_id=debt.id,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
    )

    context = {
        'debt': debt,
        'payments': payments,
        'payments_with_balance': payments_with_balance,
        'primary_payment_method': primary_payment_method,
        'latest_gcash_payment': latest_gcash_payment,
        'latest_cash_payment': latest_cash_payment,
        'total_paid': running_paid,
        'remaining_balance': debt.balance,
    }

    return render(request, 'admin/debt_detail.html', context)


@user_passes_test(is_superuser)
def admin_payments(request):
    """Admin view to list and manage payments."""
    from .models import Payment, AdminActivityLog
    
    payments = Payment.objects.select_related('debt', 'payer', 'debt__creditor', 'debt__debtor').order_by('-created_at')
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_payments',
        description=f'Admin {request.user.username} viewed payments list',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
    
    context = {
        'payments': payments,
    }
    
    return render(request, 'admin/payments.html', context)


@user_passes_test(is_superuser)
def admin_approve_payment(request, payment_id):
    """Admin action to approve a payment."""
    from .models import Payment, AdminActivityLog
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        payment.status = 'completed'
        payment.verified_at = timezone.now()
        payment.save()
        
        # Update debt status and paid amount
        debt = payment.debt
        debt.paid_amount += payment.amount
        debt.update_payment_status()
        
        # Log activity
        AdminActivityLog.objects.create(
            user=request.user,
            action='approve_payment',
            description=f'Admin {request.user.username} approved payment #{payment.receipt_no}',
            related_id=payment.id,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        messages.success(request, f'Payment #{payment.receipt_no} has been approved.')
        return redirect('admin_payments')
    
    return redirect('admin_payments')


@user_passes_test(is_superuser)
def admin_reject_payment(request, payment_id):
    """Admin action to reject a payment."""
    from .models import Payment, AdminActivityLog
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        payment.status = 'rejected'
        payment.save()
        
        # Log activity
        AdminActivityLog.objects.create(
            user=request.user,
            action='reject_payment',
            description=f'Admin {request.user.username} rejected payment #{payment.receipt_no}',
            related_id=payment.id,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        messages.success(request, f'Payment #{payment.receipt_no} has been rejected.')
        return redirect('admin_payments')
    
    return redirect('admin_payments')


@user_passes_test(is_superuser)
def admin_activity(request):
    """Admin view to see activity log."""
    from .models import AdminActivityLog
    
    activities = AdminActivityLog.objects.select_related('user').order_by('-timestamp')
    
    # Log activity
    AdminActivityLog.objects.create(
        user=request.user,
        action='view_activity',
        description=f'Admin {request.user.username} viewed activity log',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )
    
    context = {
        'activities': activities,
    }
    
    return render(request, 'admin/activity.html', context)


# ========================================
# CUSTOM CRUD INTERFACE - USERS
# ========================================
@user_passes_test(is_superuser)
def users_list(request):
    """List all users with custom UI."""
    users = CustomUser.objects.all().order_by('-date_joined')
    context = {
        'users': users,
        'total_users': users.count(),
        'page_title': 'Users Management',
        'page_description': 'Manage all system users',
    }
    return render(request, 'custom_admin/users_list.html', context)


@user_passes_test(is_superuser)
def users_add(request):
    """Add new user with custom form."""
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            account_type = request.POST.get('account_type')
            password = request.POST.get('password')
            
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return render(request, 'custom_admin/users_form.html', {
                    'page_title': 'Add User',
                    'form_action': 'add',
                })
            
            user = CustomUser.objects.create_user(
                username=username,
                full_name=full_name,
                account_type=account_type,
                password=password,
                email=email,
            )
            messages.success(request, f'User {username} created successfully')
            return redirect('users_list')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    context = {
        'page_title': 'Add User',
        'form_action': 'add',
    }
    return render(request, 'custom_admin/users_form.html', context)


@user_passes_test(is_superuser)
def users_edit(request, user_id):
    """Edit user with custom form."""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        try:
            user.full_name = request.POST.get('full_name', user.full_name)
            user.email = request.POST.get('email', user.email)
            user.account_type = request.POST.get('account_type', user.account_type)
            user.is_active = request.POST.get('is_active') == 'on'
            user.save()
            messages.success(request, f'User {user.username} updated successfully')
            return redirect('users_list')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'user': user,
        'page_title': f'Edit User - {user.username}',
        'form_action': 'edit',
    }
    return render(request, 'custom_admin/users_form.html', context)


@user_passes_test(is_superuser)
def users_delete(request, user_id):
    """Delete user."""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.user.id == user.id:
        messages.error(request, 'Cannot delete your own account')
        return redirect('users_list')
    
    username = user.username
    user.delete()
    messages.success(request, f'User {username} deleted successfully')
    return redirect('users_list')


# ========================================
# CUSTOM CRUD INTERFACE - CREDITORS
# ========================================
@user_passes_test(is_superuser)
def creditors_list(request):
    """List all creditors with custom UI."""
    creditors = CustomUser.objects.filter(account_type='creditor').order_by('-date_joined')
    context = {
        'users': creditors,
        'total_users': creditors.count(),
        'page_title': 'Creditors Management',
        'page_description': 'Manage all creditors in the system',
    }
    return render(request, 'custom_admin/users_list.html', context)


@user_passes_test(is_superuser)
def creditors_add(request):
    """Add new creditor with custom form."""
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return render(request, 'custom_admin/users_form.html', {
                    'page_title': 'Add Creditor',
                    'form_action': 'add',
                    'account_type': 'creditor',
                })
            
            user = CustomUser.objects.create_user(
                username=username,
                full_name=full_name,
                account_type='creditor',
                password=password,
                email=email,
            )
            messages.success(request, f'Creditor {username} created successfully')
            return redirect('creditors_list')
        except Exception as e:
            messages.error(request, f'Error creating creditor: {str(e)}')
    
    context = {
        'page_title': 'Add Creditor',
        'form_action': 'add',
        'account_type': 'creditor',
    }
    return render(request, 'custom_admin/users_form.html', context)


@user_passes_test(is_superuser)
def creditors_edit(request, user_id):
    """Edit creditor with custom form."""
    user = get_object_or_404(CustomUser, id=user_id, account_type='creditor')
    
    if request.method == 'POST':
        try:
            user.full_name = request.POST.get('full_name', user.full_name)
            user.email = request.POST.get('email', user.email)
            user.is_active = request.POST.get('is_active') == 'on'
            user.save()
            messages.success(request, f'Creditor {user.username} updated successfully')
            return redirect('creditors_list')
        except Exception as e:
            messages.error(request, f'Error updating creditor: {str(e)}')
    
    context = {
        'user': user,
        'page_title': f'Edit Creditor - {user.username}',
        'form_action': 'edit',
        'account_type': 'creditor',
    }
    return render(request, 'custom_admin/users_form.html', context)


@user_passes_test(is_superuser)
def creditors_delete(request, user_id):
    """Delete creditor."""
    user = get_object_or_404(CustomUser, id=user_id, account_type='creditor')
    username = user.username
    user.delete()
    messages.success(request, f'Creditor {username} deleted successfully')
    return redirect('creditors_list')


# ========================================
# CUSTOM CRUD INTERFACE - DEBTORS
# ========================================
@user_passes_test(is_superuser)
def debtors_list(request):
    """List all debtors with custom UI."""
    debtors = CustomUser.objects.filter(account_type='debtor').order_by('-date_joined')
    context = {
        'users': debtors,
        'total_users': debtors.count(),
        'page_title': 'Debtors Management',
        'page_description': 'Manage all debtors in the system',
    }
    return render(request, 'custom_admin/users_list.html', context)


@user_passes_test(is_superuser)
def debtors_add(request):
    """Add new debtor with custom form."""
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return render(request, 'custom_admin/users_form.html', {
                    'page_title': 'Add Debtor',
                    'form_action': 'add',
                    'account_type': 'debtor',
                })
            
            user = CustomUser.objects.create_user(
                username=username,
                full_name=full_name,
                account_type='debtor',
                password=password,
                email=email,
            )
            messages.success(request, f'Debtor {username} created successfully')
            return redirect('debtors_list')
        except Exception as e:
            messages.error(request, f'Error creating debtor: {str(e)}')
    
    context = {
        'page_title': 'Add Debtor',
        'form_action': 'add',
        'account_type': 'debtor',
    }
    return render(request, 'custom_admin/users_form.html', context)


@user_passes_test(is_superuser)
def debtors_edit(request, user_id):
    """Edit debtor with custom form."""
    user = get_object_or_404(CustomUser, id=user_id, account_type='debtor')
    
    if request.method == 'POST':
        try:
            user.full_name = request.POST.get('full_name', user.full_name)
            user.email = request.POST.get('email', user.email)
            user.is_active = request.POST.get('is_active') == 'on'
            user.save()
            messages.success(request, f'Debtor {user.username} updated successfully')
            return redirect('debtors_list')
        except Exception as e:
            messages.error(request, f'Error updating debtor: {str(e)}')
    
    context = {
        'user': user,
        'page_title': f'Edit Debtor - {user.username}',
        'form_action': 'edit',
        'account_type': 'debtor',
    }
    return render(request, 'custom_admin/users_form.html', context)


@user_passes_test(is_superuser)
def debtors_delete(request, user_id):
    """Delete debtor."""
    user = get_object_or_404(CustomUser, id=user_id, account_type='debtor')
    username = user.username
    user.delete()
    messages.success(request, f'Debtor {username} deleted successfully')
    return redirect('debtors_list')


# ========================================
# CUSTOM CRUD INTERFACE - DEBTS
# ========================================
@user_passes_test(is_superuser)
def debts_list(request):
    """List all debts with custom UI."""
    debts = Debt.objects.select_related('creditor', 'debtor').order_by('-date_created')
    context = {
        'debts': debts,
        'total_debts': debts.count(),
        'page_title': 'Debts Management',
        'page_description': 'Manage all debts in the system',
    }
    return render(request, 'custom_admin/debts_list.html', context)


@user_passes_test(is_superuser)
def debts_add(request):
    """Add new debt with custom form."""
    if request.method == 'POST':
        try:
            creditor_id = request.POST.get('creditor')
            debtor_id = request.POST.get('debtor')
            debt_type = request.POST.get('type')
            amount = request.POST.get('amount')
            product_name = request.POST.get('product_name')
            description = request.POST.get('description')
            
            creditor = get_object_or_404(CustomUser, id=creditor_id)
            debtor = get_object_or_404(CustomUser, id=debtor_id)
            
            debt = Debt.objects.create(
                creditor=creditor,
                debtor=debtor,
                type=debt_type,
                amount=amount if debt_type == 'money' else 0,
                product_name=product_name if debt_type == 'product' else '',
                description=description,
            )
            messages.success(request, f'Debt created successfully')
            return redirect('debts_list')
        except Exception as e:
            messages.error(request, f'Error creating debt: {str(e)}')
    
    creditors = CustomUser.objects.filter(account_type='creditor')
    debtors = CustomUser.objects.filter(account_type='debtor')
    
    context = {
        'creditors': creditors,
        'debtors': debtors,
        'page_title': 'Add Debt',
        'form_action': 'add',
    }
    return render(request, 'custom_admin/debts_form.html', context)


@user_passes_test(is_superuser)
def debts_edit(request, debt_id):
    """Edit debt with custom form."""
    debt = get_object_or_404(Debt, id=debt_id)
    
    if request.method == 'POST':
        try:
            debt.type = request.POST.get('type', debt.type)
            debt.amount = request.POST.get('amount', debt.amount) if debt.type == 'money' else 0
            debt.product_name = request.POST.get('product_name', debt.product_name) if debt.type == 'product' else ''
            debt.description = request.POST.get('description', debt.description)
            debt.status = request.POST.get('status', debt.status)
            debt.save()
            messages.success(request, f'Debt updated successfully')
            return redirect('debts_list')
        except Exception as e:
            messages.error(request, f'Error updating debt: {str(e)}')
    
    creditors = CustomUser.objects.filter(account_type='creditor')
    debtors = CustomUser.objects.filter(account_type='debtor')
    
    context = {
        'debt': debt,
        'creditors': creditors,
        'debtors': debtors,
        'page_title': f'Edit Debt',
        'form_action': 'edit',
    }
    return render(request, 'custom_admin/debts_form.html', context)


@user_passes_test(is_superuser)
def debts_delete(request, debt_id):
    """Delete debt."""
    debt = get_object_or_404(Debt, id=debt_id)
    debt.delete()
    messages.success(request, f'Debt deleted successfully')
    return redirect('debts_list')