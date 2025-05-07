import json
import os
import sys
import django
from datetime import datetime, timedelta

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'services_ai.settings')
django.setup()

from business.models import Business, ServiceItem, ServiceOffering
from django.http import HttpRequest
from ai_agent.api_views import book_appointment

def create_test_request():
    # Get a valid business ID from the database
    business = Business.objects.get(id="d367b30bc88d45a6a8a8fc488f15a0a7")
    if not business:
        print("No businesses found in the database. Please create a business first.")
        return None
    
    business_id = str(business.id)
    print(f"Using business: {business.name} (ID: {business_id})")
    
    # Get a valid service name
    service = ServiceOffering.objects.filter(business=business, is_active=True).first()
    if not service:
        print("No services found for this business. Using 'Deep Cleaning' as a placeholder.")
        service_name = "Deep Cleaning"
    else:
        service_name = service.name
        print(f"Using service: {service_name}")
    
    # Get service items for this business
    service_items = ServiceItem.objects.filter(business=business, is_active=True)
    service_item_data = {}
    
    if service_items.exists():
        # Add the first service item to our request
        service_item = service_items.first()
        service_item_data[service_item.identifier] = 1
        print(f"Adding service item: {service_item.name} (ID: {service_item.identifier})")
    
    # Create test data
    test_data = {
        "args": {
            "name": "Test Customer",
            "email": "test@example.com",
            "phone": "+1234567890",
            "type_of_service": service_name,
            "bedrooms": 3,
            "bathroom": 2,
            "square_feet": 1500,
            "appointment_date_time": "tomorrow at 2pm",
            "address": "123 Main St, Anytown, USA",
            "business_id": business_id
        }
    }
    
    # Add service items to the test data
    for key, value in service_item_data.items():
        test_data["args"][key] = value
    
    # Create a mock request
    request = HttpRequest()
    request.method = 'POST'
    request.content_type = 'application/json'
    request._body = json.dumps(test_data).encode('utf-8')
    
    return request

def test_book_appointment():
    """
    Test the book_appointment function directly
    """
    try:
        # Create a test request
        request = create_test_request()
        if not request:
            return
        
        print("\nSending request to book_appointment function...")
        print(f"Request data: {request._body.decode('utf-8')}")
        
        # Call the book_appointment function directly
        response = book_appointment(request)
        
        # Print the response
        print("\nResponse:")
        print(f"Status code: {response.status_code}")
        print(f"Content: {response.content.decode('utf-8')}")
        
        # Parse the response
        response_data = json.loads(response.content)
        
        # Check if booking was successful
        if response_data.get('success'):
            print("\nBooking was successful!")
            print(f"Booking ID: {response_data.get('booking_id')}")
        else:
            print("\nBooking failed.")
            print(f"Error message: {response_data.get('message')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_book_appointment()
