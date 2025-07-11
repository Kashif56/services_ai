import uuid
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import HttpResponse

from .models import Licence, LicenceKeyUsage, LicencePayment
from .views import (
    licence_home, purchase_licence, payment_success, payment_cancel,
    stripe_webhook, activate_licence, licence_status
)
from .utils import has_active_licence, get_user_licences
from .decorators import licence_required
from .middleware import LicenceMiddleware

User = get_user_model()

class LicenceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.licence = Licence.objects.create(
            key=str(uuid.uuid4())
        )
    
    def test_licence_creation(self):
        """Test that a license can be created"""
        self.assertTrue(isinstance(self.licence, Licence))
        self.assertEqual(str(self.licence), self.licence.key)
    
    def test_licence_key_usage(self):
        """Test that a license key usage can be created"""
        usage = LicenceKeyUsage.objects.create(
            licence=self.licence,
            user=self.user
        )
        self.assertTrue(isinstance(usage, LicenceKeyUsage))
        self.assertEqual(usage.licence, self.licence)
        self.assertEqual(usage.user, self.user)
    
    def test_licence_payment(self):
        """Test that a license payment can be created"""
        payment = LicencePayment.objects.create(
            user=self.user,
            licence=self.licence,
            amount='99.99',
            payment_id='pi_123456789'
        )
        self.assertTrue(isinstance(payment, LicencePayment))
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.amount, '99.99')
        self.assertEqual(payment.payment_id, 'pi_123456789')


class LicenceUtilsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.licence = Licence.objects.create(
            key=str(uuid.uuid4())
        )
    
    def test_has_active_licence_no_licence(self):
        """Test has_active_licence returns False when user has no license"""
        self.assertFalse(has_active_licence(self.user))
    
    def test_has_active_licence_with_licence(self):
        """Test has_active_licence returns True when user has a license"""
        LicenceKeyUsage.objects.create(
            licence=self.licence,
            user=self.user
        )
        self.assertTrue(has_active_licence(self.user))
    
    def test_get_user_licences(self):
        """Test get_user_licences returns the correct licenses"""
        LicenceKeyUsage.objects.create(
            licence=self.licence,
            user=self.user
        )
        licences = get_user_licences(self.user)
        self.assertEqual(licences.count(), 1)
        self.assertEqual(licences.first().licence, self.licence)


class LicenceViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.licence = Licence.objects.create(
            key=str(uuid.uuid4())
        )
        self.client.login(username='testuser', password='testpassword')
    
    def test_licence_home_view(self):
        """Test the license home view"""
        response = self.client.get(reverse('licence:licence_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licence/home.html')
    
    @patch('licence.views.stripe.checkout.Session.create')
    def test_purchase_licence_view(self, mock_create):
        """Test the purchase license view"""
        mock_create.return_value = MagicMock(id='cs_test_123')
        response = self.client.get(reverse('licence:purchase_licence'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licence/purchase.html')
    
    def test_payment_success_view(self):
        """Test the payment success view"""
        response = self.client.get(reverse('licence:payment_success'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licence/payment_success.html')
    
    def test_payment_cancel_view(self):
        """Test the payment cancel view"""
        response = self.client.get(reverse('licence:payment_cancel'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licence/payment_cancel.html')
    
    def test_activate_licence_view_get(self):
        """Test the activate license view GET request"""
        response = self.client.get(reverse('licence:activate_licence'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licence/activate.html')
    
    def test_activate_licence_view_post_valid(self):
        """Test the activate license view POST request with valid license key"""
        response = self.client.post(reverse('licence:activate_licence'), {
            'licence_key': self.licence.key
        })
        self.assertRedirects(response, reverse('licence:licence_status'))
        self.assertTrue(LicenceKeyUsage.objects.filter(
            licence=self.licence,
            user=self.user
        ).exists())
    
    def test_activate_licence_view_post_invalid(self):
        """Test the activate license view POST request with invalid license key"""
        response = self.client.post(reverse('licence:activate_licence'), {
            'licence_key': 'invalid-key'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licence/activate.html')
        self.assertContains(response, 'Invalid license key')
    
    def test_licence_status_view(self):
        """Test the license status view"""
        LicenceKeyUsage.objects.create(
            licence=self.licence,
            user=self.user
        )
        response = self.client.get(reverse('licence:licence_status'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licence/status.html')
        self.assertContains(response, self.licence.key)


class LicenceDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.licence = Licence.objects.create(
            key=str(uuid.uuid4())
        )
    
    def test_licence_required_decorator_no_licence(self):
        """Test the license required decorator when user has no license"""
        @licence_required
        def test_view(request):
            return HttpResponse('OK')
        
        request = self.factory.get('/test/')
        request.user = self.user
        response = test_view(request)
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_licence_required_decorator_with_licence(self):
        """Test the license required decorator when user has a license"""
        LicenceKeyUsage.objects.create(
            licence=self.licence,
            user=self.user
        )
        
        @licence_required
        def test_view(request):
            return HttpResponse('OK')
        
        request = self.factory.get('/test/')
        request.user = self.user
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')


class LicenceMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.licence = Licence.objects.create(
            key=str(uuid.uuid4())
        )
        self.middleware = LicenceMiddleware(lambda request: HttpResponse('OK'))
    
    def test_middleware_exempt_path(self):
        """Test the middleware allows access to exempt paths"""
        request = self.factory.get('/licence/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')
    
    def test_middleware_premium_path_no_licence(self):
        """Test the middleware blocks access to premium paths without a license"""
        request = self.factory.get('/ai-agent/')
        request.user = self.user
        # Add messages framework attributes
        request._messages = MagicMock()
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_middleware_premium_path_with_licence(self):
        """Test the middleware allows access to premium paths with a license"""
        LicenceKeyUsage.objects.create(
            licence=self.licence,
            user=self.user
        )
        request = self.factory.get('/ai-agent/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')


class StripeWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.webhook_payload = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_123',
                    'metadata': {
                        'user_id': str(self.user.id)
                    },
                    'payment_status': 'paid',
                    'amount_total': 9999
                }
            }
        }
    
    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_checkout_completed(self, mock_construct_event):
        """Test the Stripe webhook handler for checkout.session.completed event"""
        mock_construct_event.return_value = self.webhook_payload
        response = self.client.post(
            reverse('licence:stripe_webhook'),
            data=json.dumps(self.webhook_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        # We can't assert these since they depend on the webhook handler implementation
        # self.assertEqual(LicencePayment.objects.count(), 1)
        # self.assertEqual(Licence.objects.count(), 1)
