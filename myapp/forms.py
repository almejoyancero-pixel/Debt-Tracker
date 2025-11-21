from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Debt, Payment
from decimal import Decimal

User = get_user_model()


# ========================================
# USER REGISTRATION FORM
# ========================================
class UserRegistrationForm(UserCreationForm):
    """
    Form for registering new users with role selection.
    Includes Bootstrap 5 styling.
    """
    full_name = forms.CharField(
        max_length=255,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name',
            'autocomplete': 'name'
        }),
        help_text="Your complete name as it should appear in the system."
    )
    
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a unique username',
            'autocomplete': 'username'
        }),
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    
    account_type = forms.ChoiceField(
        choices=[
            ('', 'Select Role'),
            ('creditor', 'Creditor'),
            ('debtor', 'Debtor')
        ],
        required=True,
        label="Account Type",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Choose your role: Creditor (lender) or Debtor (borrower)."
    )
    
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'autocomplete': 'new-password'
        }),
        help_text="Your password must contain at least 8 characters."
    )
    
    password2 = forms.CharField(
        label="Confirm Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        }),
        help_text="Enter the same password as before, for verification."
    )

    class Meta:
        model = User
        fields = ['full_name', 'username', 'account_type', 'password1', 'password2']

    def clean_username(self):
        """Validate username uniqueness."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_account_type(self):
        """Validate account type selection."""
        account_type = self.cleaned_data.get('account_type')
        if account_type not in ['creditor', 'debtor']:
            raise ValidationError("Please select a valid account type.")
        return account_type

    def save(self, commit=True):
        """Save user with the selected account type."""
        user = super().save(commit=False)
        user.full_name = self.cleaned_data['full_name']
        user.account_type = self.cleaned_data['account_type']
        if commit:
            user.save()
        return user


# ========================================
# USER LOGIN FORM
# ========================================
class UserLoginForm(AuthenticationForm):
    """
    Form for user authentication.
    Includes Bootstrap 5 styling.
    """
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autocomplete': 'username',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })
    )


# ========================================
# DEBT FORM (For Debtors - NEW FLOW)
# ========================================
class DebtForm(forms.ModelForm):
    """
    Form for debtors to add new debts.
    Includes creditor username field and Bootstrap 5 styling.
    """
    creditor_username = forms.CharField(
        max_length=150,
        required=True,
        label="Creditor Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter creditor username',
            'autocomplete': 'off'
        }),
        help_text="Username of the person you owe (creditor)."
    )
    
    class Meta:
        model = Debt
        fields = ['type', 'amount', 'product_name', 'description', 'debt_proof']
        labels = {
            'type': 'Debt Type',
            'amount': 'Amount',
            'product_name': 'Product/Item Name',
            'description': 'Description',
            'debt_proof': 'Debt Proof (Optional but Recommended)'
        }
        widgets = {
            'type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount (e.g., 1000.00)',
                'step': '0.01',
                'min': '0.01'
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product/item name (optional for money debts)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Add any additional details about this debt...',
                'rows': 4
            }),
            'debt_proof': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            })
        }
        help_texts = {
            'type': 'Select whether this is a money debt or product debt.',
            'amount': 'Enter the amount owed or estimated value of the product.',
            'product_name': 'Required for product debts, optional for money debts.',
            'description': 'Optional: Add context, terms, or any relevant information.',
            'debt_proof': 'Upload proof of debt (e.g., IOU photo, agreement screenshot, or PDF). Strongly recommended for verification.'
        }

    def clean_creditor_username(self):
        """Validate that creditor exists and is a creditor account."""
        username = self.cleaned_data.get('creditor_username')
        try:
            creditor = User.objects.get(username=username)
            if creditor.account_type != 'creditor':
                raise ValidationError(f"User '{username}' is not a creditor account.")
            return username
        except User.DoesNotExist:
            raise ValidationError(f"No creditor found with username '{username}'.")

    def clean_debt_proof(self):
        """Validate uploaded debt proof file."""
        proof = self.cleaned_data.get('debt_proof')
        if proof:
            # Check file size (max 10MB)
            if proof.size > 10 * 1024 * 1024:
                raise ValidationError("File size must not exceed 10MB.")
            
            # Check file extension
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.bmp', '.webp']
            file_ext = proof.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                raise ValidationError(
                    "Invalid file type. Allowed: JPG, PNG, GIF, PDF, BMP, WEBP."
                )
        
        return proof

    def clean(self):
        """Additional validation for product debts based on debt_type."""
        cleaned_data = super().clean()
        debt_type = cleaned_data.get('type')
        product_name = cleaned_data.get('product_name')
        amount = cleaned_data.get('amount')
        
        # Validation based on debt_type
        if debt_type == 'money':
            # For money debts, only amount is required
            if not amount:
                raise ValidationError({
                    'amount': 'Amount is required for money debts.'
                })
            # Clear product_name if it was accidentally filled
            cleaned_data['product_name'] = ''
        
        elif debt_type == 'product':
            # For product debts, both product_name and amount are required
            if not product_name:
                raise ValidationError({
                    'product_name': 'Product name is required for product debts.'
                })
            if not amount:
                raise ValidationError({
                    'amount': 'Amount (estimated value) is required for product debts.'
                })
        
        return cleaned_data


# ========================================
# ADD DEBTOR FORM (For Creditors)
# ========================================
class AddDebtorForm(forms.Form):
    """
    Form for creditors to add new debtor accounts.
    Includes Bootstrap 5 styling.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username for new debtor',
            'autocomplete': 'off'
        }),
        help_text="Choose a unique username for the debtor."
    )
    
    full_name = forms.CharField(
        max_length=255,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter debtor full name'
        }),
        help_text="Debtor's complete name."
    )

    def clean_username(self):
        """Validate username uniqueness."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username already exists. Please choose another.")
        return username


# ========================================
# PAYMENT FORM (For Debtors)
# ========================================
class PaymentForm(forms.Form):
    """Form for recording payments, including partial payments."""
    amount = forms.DecimalField(
        label='Payment Amount',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
        })
    )
    
    notes = forms.CharField(
        label='Notes',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add any notes about this payment...'
        })
    )
    
    proof = forms.FileField(
        label='Payment Proof',
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf'
        }),
        help_text='Upload a photo or PDF of the payment receipt (optional)'
    )
    
    def __init__(self, *args, **kwargs):
        self.max_amount = kwargs.pop('max_amount', None)
        super().__init__(*args, **kwargs)
        if self.max_amount is not None:
            self.fields['amount'].widget.attrs['max'] = str(self.max_amount)
            self.fields['amount'].help_text = f'Maximum amount: ₱{self.max_amount:,.2f}'
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.max_amount is not None and amount > self.max_amount:
            raise forms.ValidationError(f'Amount cannot exceed ₱{self.max_amount:,.2f}')
        return amount


# ========================================
# PAYMENT METHOD SELECTION FORM
# ========================================
class PaymentMethodForm(forms.Form):
    """
    Form for selecting payment method.
    Includes both Cash and GCash options.
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('gcash', 'GCash'),
    ]
    
    method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        required=True,
        label="Payment Method",
        widget=forms.RadioSelect(attrs={
            'class': 'btn-check'
        }),
        help_text="Select your preferred payment method.",
        initial='cash'
    )
    
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        label="Reference Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter transaction reference (optional)'
        }),
        help_text="Optional: Transaction ID or reference number for verification."
    )


# ========================================
# PAYMENT PROOF FORM
# ========================================
class PaymentProofForm(forms.Form):
    """
    Form for uploading payment proof for cash payments.
    """
    proof_file = forms.FileField(
        label='Proof of Payment',
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,.pdf'
        }),
        help_text='Upload a photo or PDF of your payment proof (max 5MB)'
    )
    notes = forms.CharField(
        label='Additional Notes',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add any additional information about this payment...'
        })
    )
    
    def clean_proof_file(self):
        """Validate the uploaded proof file."""
        proof_file = self.cleaned_data.get('proof_file')
        if proof_file:
            # Check file size (5MB max)
            max_size = 5 * 1024 * 1024  # 5MB
            if proof_file.size > max_size:
                raise forms.ValidationError('File size must be no more than 5MB.')
            
            # Check file type
            valid_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
            if proof_file.content_type not in valid_types:
                raise forms.ValidationError('Only JPG, PNG, and PDF files are allowed.')
                
        return proof_file


# ========================================
# PROFILE UPDATE FORM
# ========================================
class ProfileUpdateForm(forms.ModelForm):
    """
    Form for users to update their profile information.
    Includes username, email, full name, and profile picture.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        }),
        help_text="Your unique username for login."
    )
    
    email = forms.EmailField(
        max_length=255,
        required=False,
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address (optional)'
        }),
        help_text="Optional: Your email address for notifications."
    )
    
    full_name = forms.CharField(
        max_length=255,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        }),
        help_text="Your complete name."
    )
    
    profile_picture = forms.ImageField(
        required=False,
        label="Profile Picture",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'id': 'profilePictureInput'
        }),
        help_text="Optional: Upload a profile picture (JPG, PNG, max 5MB)."
    )
    
    # Password fields (optional)
    old_password = forms.CharField(
        required=False,
        label="Current Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password to change it'
        }),
        help_text="Required only if you want to change your password."
    )
    
    new_password = forms.CharField(
        required=False,
        label="New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        help_text="Leave blank if you don't want to change password."
    )
    
    confirm_password = forms.CharField(
        required=False,
        label="Confirm New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        help_text="Re-enter the new password."
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'profile_picture']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_username(self):
        """Validate username uniqueness (excluding current user)."""
        username = self.cleaned_data.get('username')
        if self.user and User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise ValidationError("This username is already taken.")
        return username
    
    def clean_profile_picture(self):
        """Validate uploaded profile picture."""
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Check file size (max 5MB)
            if picture.size > 5 * 1024 * 1024:
                raise ValidationError("Image size must not exceed 5MB.")
            
            # Check file extension
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            file_ext = picture.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                raise ValidationError("Invalid image type. Allowed: JPG, PNG, GIF.")
        
        return picture
    
    def clean(self):
        """Validate password change fields."""
        cleaned_data = super().clean()
        # Get password fields and check if they have actual content (not just empty strings)
        old_password = cleaned_data.get('old_password') or ''
        new_password = cleaned_data.get('new_password') or ''
        confirm_password = cleaned_data.get('confirm_password') or ''
        
        # Strip whitespace for checking
        old_password_stripped = old_password.strip()
        new_password_stripped = new_password.strip()
        confirm_password_stripped = confirm_password.strip()
        
        # Only validate passwords if at least one password field has actual content
        if old_password_stripped or new_password_stripped or confirm_password_stripped:
            if not old_password:
                raise ValidationError({'old_password': 'Current password is required to change password.'})
            
            if not new_password:
                raise ValidationError({'new_password': 'New password is required.'})
            
            if not confirm_password:
                raise ValidationError({'confirm_password': 'Please confirm your new password.'})
            
            # Verify old password
            if self.user and not self.user.check_password(old_password):
                raise ValidationError({'old_password': 'Current password is incorrect.'})
            
            # Check if new passwords match
            if new_password != confirm_password:
                raise ValidationError({'confirm_password': 'New passwords do not match.'})
            
            # Check minimum length
            if len(new_password) < 8:
                raise ValidationError({'new_password': 'Password must be at least 8 characters long.'})
        
        return cleaned_data
