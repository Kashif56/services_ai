# Booking Widget Setup Guide

## Overview

The Booking Widget is a fully embeddable JavaScript widget that allows third-party websites and AI-generated websites to integrate your booking system seamlessly. Clients can book appointments without needing to visit your main website or create an account.

## Features

- **Multi-step Form**: 5-step booking process (Client Info → Service → Items → Date & Time → Confirm)
- **Service Selection**: Visual service cards with pricing and duration
- **Dynamic Service Items**: Supports all field types (text, number, select, boolean, textarea)
- **Staff Availability**: Real-time availability checking with alternate timeslots
- **Custom Fields**: Business-specific custom fields support
- **Real-time Pricing**: Live price calculation with tax
- **Responsive Design**: Mobile-friendly and works on all devices
- **No Authentication**: Public API endpoints for seamless integration

## Files Created

### Backend (Python/Django)
- `bookings/widget_views.py` - Public API endpoints for widget
- Updated `bookings/urls.py` - Widget API routes

### Frontend (JavaScript/CSS)
- `static/js/booking-widget-loader.js` - Main widget loader and initializer
- `static/js/booking-widget-core.js` - Core booking form logic (modified from existing)
- `static/js/booking-widget-multistep.js` - Multi-step navigation (modified from existing)
- `static/css/booking-widget.css` - Widget styles (copied from existing)

### Templates
- `templates/bookings/widget_example.html` - Example page with documentation

## API Endpoints

All widget endpoints are public (no authentication required) and use business slug for identification:

### 1. Get Widget Configuration
```
GET /bookings/widget/{business_slug}/config/
```
Returns: Business info, services, custom fields

### 2. Get Service Items
```
GET /bookings/widget/{business_slug}/service-items/{service_id}/
```
Returns: Service items for selected service

### 3. Check Staff Availability
```
GET /bookings/widget/{business_slug}/check-availability/?date={date}&time={time}&duration_minutes={duration}&service_offering_id={service_id}
```
Returns: Available staff and alternate timeslots

### 4. Create Booking
```
POST /bookings/widget/{business_slug}/create/
Content-Type: application/json

{
  "service_type": "service_id",
  "booking_date": "2025-01-15",
  "start_time": "10:00",
  "end_time": "11:00",
  "location_type": "business",
  "location_details": "",
  "notes": "",
  "staff_member_id": "staff_id",
  "client_name": "John Doe",
  "client_email": "john@example.com",
  "client_phone": "+1234567890",
  "custom_fields": {
    "custom_field_slug": "value"
  },
  "service_items": {
    "item_id": {
      "value": "field_value",
      "quantity": 1
    }
  }
}
```

## Embedding the Widget

### Basic Embedding

Add this code to any HTML page:

```html
<!-- Booking Widget Container -->
<div id="booking-widget" 
     data-business-slug="your-business-slug"
     data-api-url="https://yourdomain.com"
     data-primary-color="#8b5cf6">
</div>

<!-- Widget Loader Script -->
<script src="https://yourdomain.com/static/js/booking-widget-loader.js"></script>
```

### Configuration Options

- **data-business-slug** (required): Your business slug from the Business model
- **data-api-url** (optional): Base URL of your API (defaults to current domain)
- **data-primary-color** (optional): Custom primary color in hex format (defaults to #8b5cf6)

### For AI-Generated Websites

When generating websites with AI, include the widget in your template:

```html
<section class="booking-section">
  <div class="container">
    <h2>Book an Appointment</h2>
    
    <!-- Booking Widget -->
    <div id="booking-widget" 
         data-business-slug="{{ business.slug }}"
         data-api-url="{{ site_url }}">
    </div>
    <script src="{{ site_url }}/static/js/booking-widget-loader.js"></script>
  </div>
</section>
```

## Widget Flow

1. **Initialization**: Widget loader fetches business configuration
2. **Step 1 - Client Info**: Collect name, email, phone, custom fields
3. **Step 2 - Service Selection**: Choose service and location type
4. **Step 3 - Service Items**: Select optional/required service items
5. **Step 4 - Date & Time**: Pick date/time, check staff availability
6. **Step 5 - Confirmation**: Review and submit booking

## Customization

### Custom Colors

```html
<div id="booking-widget" 
     data-business-slug="your-slug"
     data-primary-color="#FF6B6B">
</div>
```

### Custom CSS

```css
#booking-widget {
  --primary: #your-color;
  --primary-rgb: 255, 107, 107;
  font-family: 'Your Font', sans-serif;
}

#booking-widget .widget-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

#booking-widget .btn-primary {
  background-color: var(--primary);
  border-color: var(--primary);
}
```

## Security Considerations

1. **CSRF Exemption**: Widget endpoints use `@csrf_exempt` for public access
2. **Business Validation**: All endpoints validate business exists and is active
3. **Data Validation**: Server-side validation for all booking data
4. **Rate Limiting**: Consider adding rate limiting to prevent abuse
5. **Lead Creation**: Automatically creates leads with source='widget'

## Testing

### View Example Page

```
http://yourdomain.com/bookings/widget-example/
```

### Test Widget Locally

1. Ensure you have an active business with services configured
2. Open the widget example page
3. Complete the booking flow
4. Check that booking is created in admin panel

## Troubleshooting

### Widget Not Loading
- Check browser console for errors
- Verify business slug is correct
- Ensure business is active
- Check API URL is accessible

### Service Items Not Showing
- Verify service has associated service items
- Check service items are active
- Ensure service offering is linked to items

### Staff Availability Issues
- Verify staff members exist and are active
- Check staff working hours are configured
- Ensure no conflicting bookings exist

### Booking Creation Fails
- Check all required fields are filled
- Verify staff member is available
- Check custom field validation
- Review server logs for errors

## Integration with AI Website Builder

The widget is designed to work seamlessly with the AI website builder:

1. When generating a website, include the widget code in the template
2. Use the business slug from the website generation context
3. Widget automatically loads business configuration
4. Bookings are linked to the business automatically

## Next Steps

1. Add rate limiting to widget endpoints
2. Implement webhook notifications for new bookings
3. Add Google Analytics tracking to widget
4. Create widget preview in admin panel
5. Add multi-language support

## Support

For issues or questions:
- Check server logs: `tail -f logs/django.log`
- Review browser console for JavaScript errors
- Test API endpoints directly with curl/Postman
- Verify database records are correct
