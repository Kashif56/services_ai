from plugins.hooks import hookspec

class PluginHooks:
    """Hook specifications for the Services AI plugin system"""
    
    @hookspec
    def lead_created(self, lead, context, api):
        """Hook called when a new lead is created
        
        Args:
            lead: The lead instance that was created
            context: Dictionary containing context information including request and user
            api: Plugin API instance for safe data access
        """
    
    @hookspec
    def booking_created(self, booking, context, api):
        """Hook called when a new booking is created
        
        Args:
            booking: The booking instance that was created
            context: Dictionary containing context information including request and user
        """
    
    @hookspec
    def booking_updated(self, booking, previous_state, context, api):
        """Hook called when a booking is updated
        
        Args:
            booking: The booking instance that was updated
            previous_state: Dictionary containing the previous state of the booking
            context: Dictionary containing context information including request and user
        """
    
    @hookspec
    def dashboard_widget(self, plugin_id, context, api):
        """Hook called when dashboard widgets are rendered
        
        Args:
            plugin_id: ID of the plugin
            context: Dictionary containing context information including request and user
        """
        
    @hookspec
    def plugin_installed(self, plugin_id, plugin_info, api):
        """Hook called when the plugin is installed
        
        Args:
            plugin_id: ID of the installed plugin
            plugin_info: Dictionary containing plugin information
        """
    
    @hookspec
    def plugin_uninstalled(self, plugin_id, api):
        """Hook called when the plugin is uninstalled
        
        Args:
            plugin_id: ID of the uninstalled plugin
        """
        
    @hookspec
    def data_export(self, export_type, start_date, end_date, context, api):
        """Hook called when data is exported
        
        Args:
            export_type: Type of data to export (leads, bookings, etc.)
            start_date: Start date for data range
            end_date: End date for data range
            context: Dictionary containing context information including request and user
            
        Returns:
            List of dictionaries containing exported data
        """
    
    @hookspec
    def register_routes(self, plugin_id, api):
        """Hook to register custom URL routes
        
        Args:
            plugin_id: ID of the plugin
            
        Returns:
            List of tuples (url_pattern, view_function, name)
        """
    
    @hookspec
    def inject_head(self, plugin_id, context, api):
        """Hook to inject content into page <head>
        
        Args:
            plugin_id: ID of the plugin
            context: Dictionary containing context information
            
        Returns:
            HTML string to inject into <head>
        """
    
    @hookspec
    def inject_footer(self, plugin_id, context, api):
        """Hook to inject content into page footer
        
        Args:
            plugin_id: ID of the plugin
            context: Dictionary containing context information
            
        Returns:
            HTML string to inject into footer
        """
    
    @hookspec
    def modify_booking_form(self, plugin_id, form, context, api):
        """Hook to modify booking form fields
        
        Args:
            plugin_id: ID of the plugin
            form: The booking form instance
            context: Dictionary containing context information
            
        Returns:
            Modified form or None
        """
    
    @hookspec
    def invoice_created(self, invoice, context, api):
        """Hook called when a new invoice is created
        
        Args:
            invoice: The invoice instance that was created
            context: Dictionary containing context information
        """
    
    @hookspec
    def invoice_updated(self, invoice, previous_state, context, api):
        """Hook called when an invoice is updated
        
        Args:
            invoice: The invoice instance that was updated
            previous_state: Dictionary containing the previous state
            context: Dictionary containing context information
        """
    
    @hookspec
    def invoice_paid(self, invoice, payment_info, context, api):
        """Hook called when an invoice is paid
        
        Args:
            invoice: The invoice instance that was paid
            payment_info: Dictionary containing payment information
            context: Dictionary containing context information
        """
    
    @hookspec
    def lead_updated(self, lead, previous_state, context, api):
        """Hook called when a lead is updated
        
        Args:
            lead: The lead instance that was updated
            previous_state: Dictionary containing the previous state
            context: Dictionary containing context information
        """
    
    @hookspec
    def lead_deleted(self, lead_id, lead_data, context, api):
        """Hook called when a lead is deleted
        
        Args:
            lead_id: ID of the deleted lead
            lead_data: Dictionary containing lead data before deletion
            context: Dictionary containing context information
        """
    
    @hookspec
    def booking_deleted(self, booking_id, booking_data, context, api):
        """Hook called when a booking is deleted
        
        Args:
            booking_id: ID of the deleted booking
            booking_data: Dictionary containing booking data before deletion
            context: Dictionary containing context information
        """
    
    @hookspec
    def booking_confirmed(self, booking, context, api):
        """Hook called when a booking is confirmed
        
        Args:
            booking: The booking instance that was confirmed
            context: Dictionary containing context information
        """
    
    @hookspec
    def booking_cancelled(self, booking, reason, context, api):
        """Hook called when a booking is cancelled
        
        Args:
            booking: The booking instance that was cancelled
            reason: Cancellation reason
            context: Dictionary containing context information
        """
    
    @hookspec
    def user_registered(self, user, context, api):
        """Hook called when a new user registers
        
        Args:
            user: The user instance that was created
            context: Dictionary containing context information
        """
    
    @hookspec
    def user_login(self, user, context, api):
        """Hook called when a user logs in
        
        Args:
            user: The user instance that logged in
            context: Dictionary containing context information including request
        """
    
    @hookspec
    def user_logout(self, user, context, api):
        """Hook called when a user logs out
        
        Args:
            user: The user instance that logged out
            context: Dictionary containing context information
        """
    
    @hookspec
    def business_created(self, business, context, api):
        """Hook called when a new business is created
        
        Args:
            business: The business instance that was created
            context: Dictionary containing context information
        """
    
    @hookspec
    def business_updated(self, business, previous_state, context, api):
        """Hook called when a business is updated
        
        Args:
            business: The business instance that was updated
            previous_state: Dictionary containing the previous state
            context: Dictionary containing context information
        """
    
    @hookspec
    def email_sent(self, recipient, subject, template, context, api):
        """Hook called when an email is sent
        
        Args:
            recipient: Email recipient
            subject: Email subject
            template: Email template used
            context: Dictionary containing context information
        """
    
    @hookspec
    def sms_sent(self, phone, message, context, api):
        """Hook called when an SMS is sent
        
        Args:
            phone: Phone number
            message: SMS message content
            context: Dictionary containing context information
        """
    
    @hookspec
    def report_generated(self, report_type, data, context, api):
        """Hook called when a report is generated
        
        Args:
            report_type: Type of report (sales, leads, bookings, etc.)
            data: Report data
            context: Dictionary containing context information
        """
    
    @hookspec
    def api_request(self, endpoint, method, data, context, api):
        """Hook called before API request is processed
        
        Args:
            endpoint: API endpoint being called
            method: HTTP method (GET, POST, etc.)
            data: Request data
            context: Dictionary containing context information
            
        Returns:
            Modified data or None
        """
    
    @hookspec
    def api_response(self, endpoint, method, response_data, context, api):
        """Hook called after API response is generated
        
        Args:
            endpoint: API endpoint that was called
            method: HTTP method used
            response_data: Response data
            context: Dictionary containing context information
            
        Returns:
            Modified response_data or None
        """
