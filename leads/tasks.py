from business.models import Business, BusinessConfiguration
from retell_agent.models import RetellAgent
from retell import Retell
from leads.models import Lead, LeadStatus
from ai_agent.models import Chat
from django.utils import timezone
from dotenv import load_dotenv
import os

load_dotenv()

client = Retell(
    api_key=os.getenv("RETELL_API_KEY"),
)



def make_call_to_lead(lead_id):
    try:
        lead = Lead.objects.get(id=lead_id)
        business = lead.business
        chat = Chat.objects.filter(phone_number=lead.phone, business=business).first()
        business_configuration = BusinessConfiguration.objects.get(business=business)
        retell_agent = RetellAgent.objects.get(business=business)

        lead_details = f"Here are the details about the lead:\nName: {lead.get_full_name()}\nPhone: {lead.phone}\nEmail: {lead.email if lead.email else 'Not provided'}\nNotes: {lead.notes if lead.notes else 'No additional notes'}"

        if business_configuration.voice_enabled and not chat.response_received:
            call_response = client.call.create_phone_call(
                    from_number=retell_agent.agent_number,
                    to_number=lead.phone,
                    override_agent_id=retell_agent.retell_agent_id,
                    retell_llm_dynamic_variables={
                        'name': lead.get_full_name(),
                        'details': lead_details
                    }
                )
            
            lead.mark_contacted('phone')
            
            print("Call Initiated")
            
            return 0
        
        return -1
    
    except Exception as e:
        print(f"Error making call: {e}")
        return -1

 
    