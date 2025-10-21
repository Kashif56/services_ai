# Booking Widget - Complete Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [API Documentation](#api-documentation)
6. [Customization](#customization)
7. [Integration Examples](#integration-examples)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Booking Widget is a fully embeddable JavaScript component that allows clients to book appointments directly from any website without authentication. It features a multi-step form, real-time availability checking, dynamic pricing, and full customization options.

### Key Features
✅ **Multi-step Form** - 5-step booking process with validation  
✅ **Real-time Availability** - Check staff availability with alternate timeslots  
✅ **Dynamic Pricing** - Live price calculation including service items and tax  
✅ **Service Items** - Support for all field types (text, number, select, boolean, textarea)  
✅ **Custom Fields** - Business-specific custom fields  
✅ **Responsive Design** - Mobile-friendly and works on all devices  
✅ **No Authentication** - Public API endpoints for seamless integration  
✅ **Easy Embedding** - Simple copy-paste integration  

---

## Quick Start

### 1. Basic Embedding

Add this code to any HTML page:

```html
<!-- Booking Widget Container -->
<div id="booking-widget" 
     data-business-slug="your-business-slug"
     data-api-url="https://yourdomain.com">
</div>

<!-- Widget Loader Script -->
<script src="https://yourdomain.com/static/js/booking-widget-loader.js"></script>
```

### 2. Replace Configuration
- `your-business-slug` - Your business slug from the database
- `https://yourdomain.com` - Your API base URL

That's it! The widget will automatically load and display the booking form.

---

## Installation

### Backend Setup

1. **API Endpoints** - Already created in `bookings/widget_views.py`
2. **URL Routes** - Already configured in `bookings/urls.py`
3. **No migrations needed** - Uses existing models

### Frontend Files

All files are already created in the `static` directory:
- `static/js/booking-widget-loader.js` - Main loader
- `static/js/booking-widget-core.js` - Core logic
- `static/js/booking-widget-multistep.js` - Multi-step navigation
- `static/css/booking-widget.css` - Styles

### Testing

Visit the example page:
```
http://localhost:8000/bookings/widget-example/
```

Or open the static HTML file:
```
static/widget-embed-example.html
```

---

## Configuration

### Data Attributes

| Attribute | Required | Default | Description |
|-----------|----------|---------|-------------|
| `data-business-slug` | ✅ Yes | - | Your business slug identifier |
| `data-api-url` | ❌ No | Current domain | Base URL of your API |
| `data-primary-color` | ❌ No | `#8b5cf6` | Custom primary color (hex) |

### Example with All Options

```html
<div id="booking-widget" 
     data-business-slug="acme-services"
     data-api-url="https://api.example.com"
     data-primary-color="#FF6B6B">
</div>
<script src="https://api.example.com/static/js/booking-widget-loader.js"></script>
```

---

## API Documentation

### Endpoint Overview

All endpoints are public (no authentication required):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/bookings/widget/{slug}/config/` | GET | Get widget configuration |
| `/bookings/widget/{slug}/service-items/{id}/` | GET | Get service items |
| `/bookings/widget/{slug}/check-availability/` | GET | Check staff availability |
| `/bookings/widget/{slug}/create/` | POST | Create booking |

### 1. Get Widget Configuration

**Request:**
```http
GET /bookings/widget/{business_slug}/config/
```

**Response:**
```json
{
  "success": true,
  "business": {
    "id": "uuid",
    "name": "Business Name",
    "slug": "business-slug",
    "logo": "https://example.com/logo.png",
    "primary_color": "#8b5cf6"
  },
  "services": [
    {
      "id": "uuid",
      "name": "Service Name",
      "description": "Service description",
      "price": 100.00,
      "duration": 60
    }
  ],
  "custom_fields": [
    {
      "id": "uuid",
      "slug": "field-slug",
      "name": "Field Name",
      "field_type": "text",
      "required": true,
      "placeholder": "Enter value",
      "help_text": "Help text",
      "options": []
    }
  ]
}
```

### 2. Get Service Items

**Request:**
```http
GET /bookings/widget/{business_slug}/service-items/{service_id}/
```

**Response:**
```json
{
  "success": true,
  "service_id": "uuid",
  "service_name": "Service Name",
  "items": [
    {
      "id": "uuid",
      "name": "Item Name",
      "description": "Item description",
      "price_type": "fixed",
      "price_value": 25.00,
      "field_type": "number",
      "field_options": [],
      "option_pricing": null,
      "is_required": false,
      "is_optional": true,
      "max_quantity": 10,
      "duration_minutes": 15
    }
  ]
}
```

### 3. Check Staff Availability

**Request:**
```http
GET /bookings/widget/{business_slug}/check-availability/
  ?date=2025-01-15
  &time=10:00
  &duration_minutes=60
  &service_offering_id=uuid
```

**Response:**
```json
{
  "success": true,
  "is_available": true,
  "reason": null,
  "available_staff": [
    {
      "id": "uuid",
      "name": "Staff Name"
    }
  ],
  "alternate_slots": []
}
```

### 4. Create Booking

**Request:**
```http
POST /bookings/widget/{business_slug}/create/
Content-Type: application/json

{
  "service_type": "service_uuid",
  "booking_date": "2025-01-15",
  "start_time": "10:00",
  "end_time": "11:00",
  "location_type": "business",
  "location_details": "",
  "notes": "Special instructions",
  "staff_member_id": "staff_uuid",
  "client_name": "John Doe",
  "client_email": "john@example.com",
  "client_phone": "+1234567890",
  "custom_fields": {
    "custom_field_slug": "value"
  },
  "service_items": {
    "item_uuid": {
      "value": "field_value",
      "quantity": 1
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Booking created successfully!",
  "booking_id": "booking_uuid"
}
```

---

## Customization

### 1. Custom Colors

```html
<div id="booking-widget" 
     data-business-slug="your-slug"
     data-primary-color="#FF6B6B">
</div>
```

### 2. Custom CSS

Add custom styles to override widget appearance:

```html
<style>
  /* Override primary color */
  #booking-widget {
    --primary: #FF6B6B;
    --primary-rgb: 255, 107, 107;
  }
  
  /* Custom header styling */
  #booking-widget .widget-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 40px;
  }
  
  /* Custom button styling */
  #booking-widget .btn-primary {
    background-color: #FF6B6B;
    border-color: #FF6B6B;
    border-radius: 25px;
  }
  
  /* Custom font */
  #booking-widget {
    font-family: 'Roboto', sans-serif;
  }
</style>
```

### 3. Custom Container Width

```html
<style>
  #booking-widget .booking-widget-container {
    max-width: 1200px;
    margin: 0 auto;
  }
</style>
```

---

## Integration Examples

### 1. WordPress Integration

```php
<!-- In your WordPress template or page -->
<div id="booking-widget" 
     data-business-slug="<?php echo get_option('business_slug'); ?>"
     data-api-url="<?php echo get_option('api_url'); ?>">
</div>
<script src="<?php echo get_option('api_url'); ?>/static/js/booking-widget-loader.js"></script>
```

### 2. React Integration

```jsx
import { useEffect } from 'react';

function BookingWidget({ businessSlug, apiUrl }) {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = `${apiUrl}/static/js/booking-widget-loader.js`;
    script.async = true;
    document.body.appendChild(script);
    
    return () => {
      document.body.removeChild(script);
    };
  }, [apiUrl]);
  
  return (
    <div 
      id="booking-widget"
      data-business-slug={businessSlug}
      data-api-url={apiUrl}
    />
  );
}
```

### 3. AI-Generated Website

```html
<!-- In your AI-generated template -->
<section class="booking-section">
  <div class="container">
    <h2>{{ booking_section_title }}</h2>
    <p>{{ booking_section_description }}</p>
    
    <div id="booking-widget" 
         data-business-slug="{{ business.slug }}"
         data-api-url="{{ site_url }}">
    </div>
    <script src="{{ site_url }}/static/js/booking-widget-loader.js"></script>
  </div>
</section>
```

### 4. Plain HTML Website

```html
<!DOCTYPE html>
<html>
<head>
  <title>Book Appointment</title>
</head>
<body>
  <h1>Book Your Appointment</h1>
  
  <div id="booking-widget" 
       data-business-slug="your-business-slug"
       data-api-url="https://yourdomain.com">
  </div>
  
  <script src="https://yourdomain.com/static/js/booking-widget-loader.js"></script>
</body>
</html>
```

---

## Troubleshooting

### Widget Not Loading

**Problem:** Widget container shows loading but never displays form

**Solutions:**
1. Check browser console for errors
2. Verify business slug is correct
3. Ensure business is active in database
4. Check API URL is accessible
5. Verify CORS settings if on different domain

```javascript
// Check in browser console
console.log(window.BookingWidget);
```

### Service Items Not Showing

**Problem:** Step 3 shows "No items available"

**Solutions:**
1. Verify service has associated service items
2. Check service items are active (`is_active=True`)
3. Ensure `ServiceOfferingItem` links exist
4. Check service offering is active

### Staff Availability Issues

**Problem:** "No staff available" message appears

**Solutions:**
1. Verify staff members exist and are active
2. Check staff working hours are configured
3. Ensure no conflicting bookings exist
4. Verify staff is assigned to the service

### Booking Creation Fails

**Problem:** Form submits but booking is not created

**Solutions:**
1. Check all required fields are filled
2. Verify staff member is available at selected time
3. Check custom field validation
4. Review server logs for errors
5. Test API endpoint directly with Postman

```bash
# Check Django logs
tail -f logs/django.log

# Test API endpoint
curl -X POST https://yourdomain.com/bookings/widget/your-slug/create/ \
  -H "Content-Type: application/json" \
  -d '{"service_type":"uuid","booking_date":"2025-01-15",...}'
```

### CORS Issues

**Problem:** API requests blocked by CORS policy

**Solution:** Add CORS headers in Django settings:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "https://third-party-website.com",
]

# Or allow all (not recommended for production)
CORS_ALLOW_ALL_ORIGINS = True
```

### Styling Issues

**Problem:** Widget styles conflict with website styles

**Solutions:**
1. Use more specific CSS selectors
2. Add `!important` to critical styles
3. Load widget CSS after website CSS
4. Use CSS isolation techniques

```css
/* Increase specificity */
#booking-widget .booking-widget-container .btn-primary {
  background-color: #8b5cf6 !important;
}
```

---

## Support & Maintenance

### Monitoring

Monitor widget performance:
- Track API response times
- Monitor error rates
- Check booking success rate
- Review user feedback

### Updates

Keep widget updated:
1. Regularly update JavaScript files
2. Test on different browsers
3. Check mobile responsiveness
4. Update documentation

### Security

Security best practices:
- Implement rate limiting on API endpoints
- Validate all input data
- Sanitize user inputs
- Use HTTPS only
- Monitor for suspicious activity

---

## License

This widget is part of the Services AI platform. All rights reserved.

---

## Contact

For support or questions:
- Email: support@servicesai.com
- Documentation: https://docs.servicesai.com
- GitHub: https://github.com/servicesai/booking-widget
