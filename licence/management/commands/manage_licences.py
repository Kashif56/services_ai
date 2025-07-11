import uuid
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from licence.models import Licence, LicenceKeyUsage

User = get_user_model()

class Command(BaseCommand):
    help = 'Manage license keys for the Services AI application'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', help='Command to run')
        
        # Create license command
        create_parser = subparsers.add_parser('create', help='Create a new license key')
        create_parser.add_argument('--count', type=int, default=1, help='Number of licenses to create')
        
        # Assign license command
        assign_parser = subparsers.add_parser('assign', help='Assign a license key to a user')
        assign_parser.add_argument('--key', required=True, help='License key to assign')
        assign_parser.add_argument('--username', required=True, help='Username to assign the license to')
        
        # Revoke license command
        revoke_parser = subparsers.add_parser('revoke', help='Revoke a license key from a user')
        revoke_parser.add_argument('--key', required=True, help='License key to revoke')
        revoke_parser.add_argument('--username', required=True, help='Username to revoke the license from')
        
        # List licenses command
        list_parser = subparsers.add_parser('list', help='List all licenses')
        list_parser.add_argument('--username', help='Filter licenses by username')
        list_parser.add_argument('--active', action='store_true', help='Filter by active licenses only')
        list_parser.add_argument('--inactive', action='store_true', help='Filter by inactive licenses only')

    def handle(self, *args, **options):
        command = options['command']
        
        if command == 'create':
            self.create_licenses(options['count'])
        elif command == 'assign':
            self.assign_license(options['key'], options['username'])
        elif command == 'revoke':
            self.revoke_license(options['key'], options['username'])
        elif command == 'list':
            self.list_licenses(options.get('username'), options.get('active'), options.get('inactive'))
        else:
            raise CommandError('Invalid command')

    def create_licenses(self, count):
        """Create new license keys"""
        created_licenses = []
        
        for _ in range(count):
            license_key = str(uuid.uuid4())
            license = Licence.objects.create(
                key=license_key
            )
            created_licenses.append(license)
            self.stdout.write(self.style.SUCCESS(f'Created license key: {license_key}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} license keys'))
        return created_licenses

    def assign_license(self, key, username):
        """Assign a license key to a user"""
        try:
            license = Licence.objects.get(key=key)
        except Licence.DoesNotExist:
            raise CommandError(f'License key {key} does not exist')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User {username} does not exist')
        
        # Check if license is already assigned to this user
        if LicenceKeyUsage.objects.filter(licence=license, user=user).exists():
            self.stdout.write(self.style.WARNING(f'License key {key} is already assigned to user {username}'))
            return
        
        # Assign license to user
        LicenceKeyUsage.objects.create(
            licence=license,
            user=user,
            activated_at=timezone.now()
        )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully assigned license key {key} to user {username}'))

    def revoke_license(self, key, username):
        """Revoke a license key from a user"""
        try:
            license = Licence.objects.get(key=key)
        except Licence.DoesNotExist:
            raise CommandError(f'License key {key} does not exist')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User {username} does not exist')
        
        # Check if license is assigned to this user
        try:
            license_usage = LicenceKeyUsage.objects.get(licence=license, user=user)
        except LicenceKeyUsage.DoesNotExist:
            raise CommandError(f'License key {key} is not assigned to user {username}')
        
        # Revoke license
        license_usage.delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully revoked license key {key} from user {username}'))

    def list_licenses(self, username=None, active=False, inactive=False):
        """List all licenses"""
        licenses = Licence.objects.all()
        
      
        # Filter by username if provided
        if username:
            try:
                user = User.objects.get(username=username)
                license_usages = LicenceKeyUsage.objects.filter(user=user).values_list('licence_id', flat=True)
                licenses = licenses.filter(id__in=license_usages)
            except User.DoesNotExist:
                raise CommandError(f'User {username} does not exist')
        
        # Display licenses
        if not licenses.exists():
            self.stdout.write(self.style.WARNING('No licenses found matching the criteria'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {licenses.count()} licenses:'))
        for license in licenses:
            status = 'Active' if license.is_active else 'Inactive'
            users = ', '.join([usage.user.username for usage in license.licencekeyusage_set.all()])
            users_text = f' (Used by: {users})' if users else ''
            
            self.stdout.write(f'- {license.key} [{status}]{users_text}')
