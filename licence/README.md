# License System for Services AI

A one-time premium licensing system for the Services AI application using Stripe for payment processing.

## Features

- One-time license purchase via Stripe
- License key generation and management
- License activation by entering a license key
- License status tracking and display
- Middleware for restricting access to premium features
- Template tags for conditional rendering based on license status

## Setup

1. Add the following environment variables to your `.env` file:

```
STRIPE_PUBLIC_KEY=your_stripe_public_key
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
LICENCE_AMOUNT=99.99
```

2. Add the license app to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'licence.apps.LicenceConfig',
    # ...
]
```

3. Add the license middleware to `MIDDLEWARE` in `settings.py`:

```python
MIDDLEWARE = [
    # ...
    'licence.middleware.LicenceMiddleware',
]
```

4. Add the license context processor to `TEMPLATES` in `settings.py`:

```python
TEMPLATES = [
    {
        # ...
        'OPTIONS': {
            'context_processors': [
                # ...
                'licence.context_processors.licence_context',
            ],
        },
    },
]
```

5. Include the license URLs in your main `urls.py`:

```python
urlpatterns = [
    # ...
    path('licence/', include('licence.urls')),
    # ...
]
```

6. Run migrations:

```
python manage.py makemigrations
python manage.py migrate
```

7. Configure your Stripe webhook endpoint in the Stripe dashboard to point to `/licence/webhook/`.

## Usage

### Middleware

The license middleware automatically checks if a user has an active license when accessing premium features. If not, they are redirected to the license home page.

### Decorator

You can use the `@licence_required` decorator to restrict access to views that require a license:

```python
from licence.decorators import licence_required

@licence_required
def premium_view(request):
    # This view is only accessible to users with an active license
    return render(request, 'premium_template.html')
```

### Template Tags

You can use the template tags to conditionally show or hide premium features in your templates:

```html
{% load licence_tags %}

{% user_has_licence as has_licence %}
{% if has_licence %}
    <!-- Show premium content -->
{% else %}
    <!-- Show upgrade prompt -->
{% endif %}

{% get_licences as user_licences %}
{% for licence in user_licences %}
    {{ licence.licence.key }}
{% endfor %}
```

### Context Processor

The license context processor adds the following variables to all templates:

- `has_active_licence`: Boolean indicating if the user has an active license
- `user_licences`: QuerySet of all licenses for the user (only available if the user is authenticated)

## License Pages

- `/licence/`: License home page showing license status and options to purchase or activate a license
- `/licence/purchase/`: License purchase page with Stripe checkout integration
- `/licence/activate/`: License activation page for entering a license key
- `/licence/status/`: License status page showing active licenses
- `/licence/success/`: Payment success page shown after a successful payment
- `/licence/cancel/`: Payment cancel page shown if the user cancels the payment

## Models

- `Licence`: Stores license keys and their status
- `LicenceKeyUsage`: Tracks which users are using which license keys
- `LicencePayment`: Tracks payments for licenses

## Utilities

- `has_active_licence(user)`: Check if a user has an active license
- `get_user_licences(user)`: Get all licenses for a user
