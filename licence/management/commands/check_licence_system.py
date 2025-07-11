from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from licence.models import Licence, LicenceKeyUsage, LicencePayment
from licence.utils import has_active_licence

User = get_user_model()

class Command(BaseCommand):
    help = 'Check and report on the license system status'

    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true', help='Show detailed information')

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        # Check Stripe settings
        self.stdout.write(self.style.NOTICE('Checking Stripe settings...'))
        stripe_public_key = getattr(settings, 'STRIPE_PUBLIC_KEY', None)
        stripe_secret_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
        stripe_webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        licence_amount = getattr(settings, 'LICENCE_AMOUNT', None)
        
        if not stripe_public_key:
            self.stdout.write(self.style.ERROR('STRIPE_PUBLIC_KEY is not set'))
        else:
            self.stdout.write(self.style.SUCCESS('STRIPE_PUBLIC_KEY is set'))
            
        if not stripe_secret_key:
            self.stdout.write(self.style.ERROR('STRIPE_SECRET_KEY is not set'))
        else:
            self.stdout.write(self.style.SUCCESS('STRIPE_SECRET_KEY is set'))
            
        if not stripe_webhook_secret:
            self.stdout.write(self.style.WARNING('STRIPE_WEBHOOK_SECRET is not set (optional but recommended)'))
        else:
            self.stdout.write(self.style.SUCCESS('STRIPE_WEBHOOK_SECRET is set'))
            
        if not licence_amount:
            self.stdout.write(self.style.ERROR('LICENCE_AMOUNT is not set'))
        else:
            self.stdout.write(self.style.SUCCESS(f'LICENCE_AMOUNT is set to {licence_amount}'))
        
        # Check license models
        self.stdout.write(self.style.NOTICE('\nChecking license models...'))
        
        # Check Licence model
        licence_count = Licence.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'Total licenses: {licence_count}'))
        
        if verbose and licence_count > 0:
            self.stdout.write(self.style.NOTICE('\nLicense details:'))
            for licence in Licence.objects.all():
                usage_count = licence.licence_key_usages.count()
                self.stdout.write(f'- {licence.key} (Used by {usage_count} users)')
        
        # Check LicenceKeyUsage model
        usage_count = LicenceKeyUsage.objects.count()
        user_count = LicenceKeyUsage.objects.values('user').distinct().count()
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal license usages: {usage_count}'))
        self.stdout.write(self.style.SUCCESS(f'Users with licenses: {user_count}'))
        
        if verbose and usage_count > 0:
            self.stdout.write(self.style.NOTICE('\nLicense usage details:'))
            for usage in LicenceKeyUsage.objects.select_related('user', 'licence'):
                self.stdout.write(f'- User: {usage.user.username}, License: {usage.licence.key}, Activated: {usage.created_at}')
        
        # Check LicencePayment model
        payment_count = LicencePayment.objects.count()
        total_amount = sum(float(payment.amount) for payment in LicencePayment.objects.all())
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal payments: {payment_count}'))
        self.stdout.write(self.style.SUCCESS(f'Total revenue: ${total_amount:.2f}'))
        
        if verbose and payment_count > 0:
            self.stdout.write(self.style.NOTICE('\nPayment details:'))
            for payment in LicencePayment.objects.select_related('user'):
                self.stdout.write(f'- User: {payment.user.username}, Amount: ${payment.amount}, Paid: {payment.paid_at}, ID: {payment.stripe_payment_id}')
        
        # Summary
        self.stdout.write(self.style.NOTICE('\nLicense system summary:'))
        if licence_count > 0 and usage_count > 0 and payment_count > 0:
            self.stdout.write(self.style.SUCCESS('License system is operational'))
        else:
            self.stdout.write(self.style.WARNING('License system may not be fully operational'))
            if licence_count == 0:
                self.stdout.write(self.style.ERROR('No licenses have been created'))
            if usage_count == 0:
                self.stdout.write(self.style.ERROR('No licenses have been activated by users'))
            if payment_count == 0:
                self.stdout.write(self.style.ERROR('No payments have been processed'))
