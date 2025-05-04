"""
LangChain Agent Implementation for SMS-based AI Assistant
This module implements a LangChain-based conversational agent that handles
SMS conversations through Twilio for appointment booking and management.
"""

from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime
import functools
import inspect

from langchain.agents import AgentExecutor
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI

from django.conf import settings
from django.utils import timezone

from business.models import Business, ServiceOffering, ServiceItem
from .models import Chat, Message, AgentConfig
from .tools import CheckAvailabilityTool, BookAppointmentTool, RescheduleAppointmentTool, CancelAppointmentTool

class LangChainAgent:
    """
    LangChain-based conversational agent for handling SMS interactions.
    This agent uses OpenAI's function calling capabilities to execute tools
    for appointment booking, rescheduling, cancellation, and availability checking.
    """
    
    def __init__(self, business_id: str, chat_id: Optional[str] = None, 
                 phone_number: Optional[str] = None, session_key: Optional[str] = None):
        """
        Initialize the LangChain agent with business and chat information.
        
        Args:
            business_id: The ID of the business this agent is representing
            chat_id: Optional ID of an existing chat to continue
            phone_number: Optional phone number for the chat
            session_key: Optional session key for web-based chats
        """
        self.business_id = business_id
        self.chat_id = chat_id
        self.phone_number = phone_number
        self.session_key = session_key
        
        # Load business information
        try:
            self.business = Business.objects.get(id=business_id)
        except Business.DoesNotExist:
            raise ValueError(f"Business with ID {business_id} not found")
        
        # Get or create chat
        self.chat = self._get_or_create_chat()
        
        # Initialize LangChain components
        self.llm = self._initialize_llm()
        self.memory = self._initialize_memory()
        self.tools = self._initialize_tools()
        self.agent = self._initialize_agent()
        self.agent_executor = self._initialize_agent_executor()
    
    def _get_or_create_chat(self) -> Chat:
        """Get existing chat or create a new one."""
        if self.chat_id:
            try:
                return Chat.objects.get(id=self.chat_id, business=self.business)
            except Chat.DoesNotExist:
                raise ValueError(f"Chat with ID {self.chat_id} not found for business {self.business.name}")
        
        # Try to find an existing chat first
        chat_kwargs = {
            'business': self.business,
        }
        
        if self.phone_number:
            chat_kwargs['phone_number'] = self.phone_number
        
        if self.session_key:
            chat_kwargs['session_key'] = self.session_key
        
        # Try to get an existing chat first
        existing_chat = Chat.objects.filter(**chat_kwargs).first()
        if existing_chat:
            # Update the is_active flag if needed
            if not existing_chat.is_active:
                existing_chat.is_active = True
                existing_chat.save(update_fields=['is_active', 'updated_at'])
            return existing_chat
        
        # Create a new chat if none exists
        return Chat.objects.create(**chat_kwargs)
    
    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the LLM with appropriate settings."""
        api_key = settings.OPENAI_API_KEY
        model_name = getattr(settings, 'OPENAI_MODEL_NAME', 'gpt-4-0125-preview')
        
        return ChatOpenAI(
            temperature=0.7,
            model=model_name,
            api_key=api_key,
            max_tokens=1024,
        )
    
    def _initialize_memory(self) -> ConversationBufferMemory:
        """Initialize conversation memory and load existing messages."""
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Load existing messages from database
        messages = self.chat.messages.all().order_by('created_at')
        
        for msg in messages:
            if msg.role == 'user':
                memory.chat_memory.add_user_message(msg.content)
            elif msg.role == 'assistant':
                memory.chat_memory.add_ai_message(msg.content)
            elif msg.role == 'system':
                # System messages are handled separately in the agent initialization
                pass
        
        return memory
    
    def _initialize_tools(self) -> List:
        """Initialize the tools for the agent."""
        print(f"[DEBUG] Initializing tools for business: {self.business.name} (ID: {self.business.id})")
        
        # Create the tools
        check_availability_tool = CheckAvailabilityTool()
        book_appointment_tool = BookAppointmentTool()
        reschedule_appointment_tool = RescheduleAppointmentTool()
        cancel_appointment_tool = CancelAppointmentTool()
        
        # Add business_id to the tools that need it
        def wrap_tool_run(tool, original_run):
            """Wrap the tool's _run method to add business_id if not provided."""
            @functools.wraps(original_run)
            def wrapped_run(*args, **kwargs):
                print(f"[DEBUG] Running {tool.name} with args: {args}, kwargs: {kwargs}")
                
                # Only add business_id if the tool accepts it
                if 'business_id' in inspect.signature(original_run).parameters:
                    if 'business_id' not in kwargs or not kwargs['business_id']:
                        kwargs['business_id'] = str(self.business.id)
                        print(f"[DEBUG] Added business_id: {kwargs['business_id']}")
                
                # Filter out kwargs that aren't accepted by the function
                valid_params = inspect.signature(original_run).parameters.keys()
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
                
                if filtered_kwargs != kwargs:
                    print(f"[DEBUG] Filtered kwargs: {kwargs} -> {filtered_kwargs}")
                
                return original_run(*args, **filtered_kwargs)
            return wrapped_run
        
        # Wrap each tool's _run method
        for tool in [check_availability_tool, book_appointment_tool, reschedule_appointment_tool, cancel_appointment_tool]:
            original_run = tool._run
            tool._run = wrap_tool_run(tool, original_run)
            print(f"[DEBUG] Wrapped {tool.name}._run method")
        
        print(f"[DEBUG] Created tools: {check_availability_tool.name}, {book_appointment_tool.name}, {reschedule_appointment_tool.name}, {cancel_appointment_tool.name}")
        
        return [
            check_availability_tool,
            book_appointment_tool,
            reschedule_appointment_tool,
            cancel_appointment_tool
        ]

    def _get_system_prompt(self) -> str:
        """
        Generate a dynamic system prompt based on business details.
        This customizes the agent's behavior for each business.
        """
        # Get agent config from database or use default
        agent_config = AgentConfig.objects.filter(business=self.business, is_active=True).first()
        
        # Get current date and time
        current_date = timezone.now().strftime("%Y-%m-%d")
        current_time = timezone.now().strftime("%H:%M")
        
        if agent_config and agent_config.prompt:
            # Use custom prompt from database
            system_prompt = agent_config.prompt
        else:
            # Generate default prompt
            business_name = self.business.name
            business_description = self.business.description or ""
            business_id = str(self.business.id)  # Convert UUID to string
            
            # Get services
            services = ServiceOffering.objects.filter(business=self.business, is_active=True)
            services_text = "\n".join([
                f"- {service.name}: {service.description or 'No description'} - ${service.price} - {service.duration} minutes"
                for service in services
            ])
            
            # Default system prompt
            system_prompt = f"""
            You are an AI assistant for {business_name}, a service-based business. 
            {business_description}
            
            Today's date is {current_date} and the current time is {current_time}.
            
            Your role is to help customers with:
            1. Answering questions about services
            2. Checking availability for appointments
            3. Booking appointments
            4. Rescheduling appointments
            5. Canceling appointments
            
            Available services:
            {services_text}
            
            When helping customers:
            - Be friendly, professional, and concise
            - Ask for all necessary information before booking
            - Confirm details before finalizing any appointment
            - Always use the correct business_id: {business_id}
            - When using dates, always convert human-readable dates (like "tomorrow", "next Monday") to YYYY-MM-DD format
            - When using times, always convert human-readable times (like "afternoon", "evening") to HH:MM format
            
            For checking availability:
            - Use the check_availability tool with the business_id: {business_id}
            - Make sure to convert dates to YYYY-MM-DD format
            - Make sure to convert times to HH:MM format
            
            For booking appointments:
            - Use the book_appointment tool with the business_id: {business_id}
            - Make sure to convert dates to YYYY-MM-DD format
            - Make sure to convert times to HH:MM format
            
            For rescheduling appointments:
            - Use the reschedule_appointment tool with the business_id: {business_id}
            - Make sure to convert dates to YYYY-MM-DD format
            - Make sure to convert times to HH:MM format
            
            For canceling appointments:
            - Use the cancel_appointment tool with the business_id: {business_id}
            
            Always maintain a conversational tone and guide the customer through the process step by step.
            """
        
        return system_prompt
    
    def _initialize_agent(self) -> OpenAIFunctionsAgent:
        """Initialize the OpenAI Functions agent."""
        print(f"[DEBUG] Initializing agent for business: {self.business.name} (ID: {self.business.id})")
        
        # Get system prompt
        system_prompt = self._get_system_prompt()
        print(f"[DEBUG] System prompt length: {len(system_prompt)}")
        
        # Create the prompt
        prompt = OpenAIFunctionsAgent.create_prompt(
            system_message=SystemMessage(content=system_prompt),
            extra_prompt_messages=[MessagesPlaceholder(variable_name="chat_history")]
        )
        
        # Create the agent
        agent = OpenAIFunctionsAgent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        print(f"[DEBUG] Agent created successfully")
        
        return agent
    
    def _initialize_agent_executor(self) -> AgentExecutor:
        """Initialize the agent executor."""
        print(f"[DEBUG] Initializing agent executor")
        
        return AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )
    
    def process_message(self, user_message: str) -> str:
        """
        Process a user message and return the agent's response.
        
        Args:
            user_message: The message from the user
            
        Returns:
            The agent's response
        """
        print(f"[DEBUG] Running agent with message: '{user_message}'")
        
        # Save user message to database
        Message.objects.create(
            chat=self.chat,
            role='user',
            content=user_message,
            created_at=timezone.now()
        )
        
        try:
            # Process with LangChain agent
            response = self.agent_executor.run(user_message)
            
            print(f"[DEBUG] Agent response: {response}")
            
            # Save assistant response to database
            Message.objects.create(
                chat=self.chat,
                role='assistant',
                content=response,
                created_at=timezone.now()
            )
            
            return response
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"[DEBUG] Error running agent: {str(e)}")
            print(f"[DEBUG] Traceback: {error_traceback}")
            
            # Save error as system message
            Message.objects.create(
                chat=self.chat,
                role='system',
                content=f"Error processing message: {str(e)}",
                created_at=timezone.now()
            )
            
            # Return a user-friendly error message
            return "I'm sorry, I encountered an error processing your request. Please try again later."
    
    def update_chat_summary(self) -> None:
        """
        Update the chat summary with key information extracted from the conversation.
        This is useful for analytics and quick reference.
        """
        # Get all messages in this chat
        messages = self.chat.messages.all().order_by('created_at')
        
        if not messages:
            return
        
        # Extract basic summary info
        message_count = messages.count()
        first_message_time = messages.first().created_at
        last_message_time = messages.last().created_at
        
        # Create a simple summary
        summary = {
            'message_count': message_count,
            'first_message': first_message_time.isoformat(),
            'last_message': last_message_time.isoformat(),
            'duration_seconds': (last_message_time - first_message_time).total_seconds(),
        }
        
        # Update the chat summary
        self.chat.summary = summary
        self.chat.save(update_fields=['summary', 'updated_at'])
