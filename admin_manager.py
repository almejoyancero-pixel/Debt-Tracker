#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import CustomUser

def check_admin():
    print("=== ADMIN USER CHECK ===")
    
    # Check all superusers
    superusers = CustomUser.objects.filter(is_superuser=True)
    print(f"Total superusers: {superusers.count()}")
    
    for user in superusers:
        print(f"- Username: {user.username}")
        print(f"  Full name: {user.full_name}")
        print(f"  Account type: {user.account_type}")
        print(f"  Is active: {user.is_active}")
        print(f"  Is staff: {user.is_staff}")
        print(f"  Is superuser: {user.is_superuser}")
        print()

def create_admin():
    print("=== CREATING NEW ADMIN ===")
    username = input("Enter admin username: ")
    password = input("Enter admin password: ")
    full_name = input("Enter full name: ")
    
    try:
        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            print(f"User {username} already exists!")
            return
        
        # Create superuser
        user = CustomUser.objects.create_superuser(
            username=username,
            full_name=full_name,
            password=password
        )
        print(f"Admin user {username} created successfully!")
        
    except Exception as e:
        print(f"Error creating admin: {e}")

def reset_admin_password():
    print("=== RESET ADMIN PASSWORD ===")
    username = input("Enter admin username: ")
    new_password = input("Enter new password: ")
    
    try:
        user = CustomUser.objects.get(username=username, is_superuser=True)
        user.set_password(new_password)
        user.save()
        print(f"Password for {username} has been reset!")
        
    except CustomUser.DoesNotExist:
        print(f"Admin user {username} not found!")
    except Exception as e:
        print(f"Error resetting password: {e}")

if __name__ == "__main__":
    while True:
        print("\n=== ADMIN MANAGEMENT ===")
        print("1. Check existing admins")
        print("2. Create new admin")
        print("3. Reset admin password")
        print("4. Exit")
        
        choice = input("Choose option (1-4): ").strip()
        
        if choice == "1":
            check_admin()
        elif choice == "2":
            create_admin()
        elif choice == "3":
            reset_admin_password()
        elif choice == "4":
            break
        else:
            print("Invalid choice!")