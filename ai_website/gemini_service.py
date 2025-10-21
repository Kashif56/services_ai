"""
Google Gemini Service for AI Website Builder
Handles all Google Gemini API interactions for generating business websites
"""

import google.generativeai as genai
from django.conf import settings
from .utils import get_business_context, build_system_prompt, build_user_prompt

def configure_gemini():
    """Configure Gemini API with API key"""
    if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
        raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in your environment variables.")
    
    genai.configure(api_key=settings.GEMINI_API_KEY)



def generate_website_with_gemini(business, ai_prompt, existing_html=None):
    """
    Generate a complete website using Google Gemini API
    
    Args:
        business: Business model instance
        ai_prompt: User's custom prompt/requirements
        existing_html: Optional existing HTML content for iterative improvements
        
    Returns:
        str: Generated HTML content
        
    Raises:
        Exception: If Gemini API call fails
    """

    
    # Configure Gemini
    configure_gemini()
    
    # Get business context
    business_context = get_business_context(business)
    
    # Build prompts
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(business_context, ai_prompt)
    
    # If existing HTML is provided, modify the user prompt for iterative improvement
    if existing_html:
        user_prompt = f"""{user_prompt}

**📄 EXISTING WEBSITE HTML:**
You are modifying an EXISTING website. Below is the current HTML code. Make the requested changes while preserving the overall structure and design unless specifically asked to change it.

```html
{existing_html}  
```

**IMPORTANT INSTRUCTIONS FOR MODIFICATION:**
1. Keep the existing design style, color scheme, and layout UNLESS the user specifically asks to change them
2. Only modify the parts that the user requested to change
3. Preserve all existing sections that weren't mentioned in the request
4. Maintain consistency with the existing design language
5. If adding new sections, match the style of existing sections
6. Return the COMPLETE modified HTML (not just the changed parts)

Now, apply the following changes: {ai_prompt}"""
    
    # Combine system and user prompts for Gemini
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Generate content
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
            )
        )
        
        # Extract generated HTML
        html_content = response.text
        
        
        # Clean up the response (remove markdown code blocks if present)
        html_content = html_content.strip()
        if html_content.startswith('```html'):
            html_content = html_content[7:]
        if html_content.startswith('```'):
            html_content = html_content[3:]
        if html_content.endswith('```'):
            html_content = html_content[:-3]
        
        html_content = html_content.strip()
        
        
        return html_content
        
    except Exception as e:
        raise Exception(f"Gemini API Error: {str(e)}")
