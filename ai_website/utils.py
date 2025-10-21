import os
from django.conf import settings
from pathlib import Path
from bookings.models import StaffMember

def create_website_directory(business_slug):
    """
    Create a directory for website files based on business slug
    Returns the directory path relative to MEDIA_ROOT
    """
    site_dir = os.path.join('sites', business_slug)
    full_path = os.path.join(settings.MEDIA_ROOT, site_dir)
    
    # Create directory if it doesn't exist
    Path(full_path).mkdir(parents=True, exist_ok=True)
    
    return site_dir


def save_html_file(business_slug, html_content):
    """
    Save HTML content to a file in the business's directory
    Returns the file path relative to MEDIA_ROOT
    
    Args:
        business_slug: URL-friendly slug of the business name
        html_content: HTML content to save
    """
    # Create website directory
    site_dir = create_website_directory(business_slug)
    
    # Define file path
    file_name = 'index.html'
    relative_path = os.path.join(site_dir, file_name)
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    
    # Write to file
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return relative_path


# Mock website generation function has been removed
# Real OpenAI integration is now in openai_service.py
def get_business_context(business):
    """
    Extract comprehensive business context for AI website generation
    
    Args:
        business: Business model instance
        
    Returns:
        dict: Structured business information
    """
    context = {
        'business_name': business.name,
        'industry': business.industry.name if business.industry else 'General',
        'description': business.description or '',
        'contact': {
            'email': business.email,
            'phone': business.phone_number,
            'address': business.address or '',
            'city': business.city or '',
            'state': business.state or '',
            'zip_code': business.zip_code or '',
        },
        'website': business.website or '',
        'services': [],
        'service_items': [],
        'staff_members': [],
    }
    
    # Get service offerings
    service_offerings = business.service_offerings.filter(is_active=True)
    for service in service_offerings:
        service_data = {
            'name': service.name,
            'description': service.description or '',
            'price': float(service.price),
            'duration': service.duration,
            'is_free': service.is_free,
        }
        context['services'].append(service_data)
    
    # Get service items
    service_items = business.service_items.filter(is_active=True)
    for item in service_items:
        item_data = {
            'name': item.name,
            'description': item.description or '',
            'price_type': item.price_type,
            'price_value': float(item.price_value),
            'field_type': item.field_type,
        }
        context['service_items'].append(item_data)
    
    # Get staff members

    staff_members = StaffMember.objects.filter(business=business, is_active=True)
    for staff in staff_members:
        staff_data = {
            'name': staff.get_full_name(),
            'role': staff.roles.first().name if staff.roles.first() else 'Team Member',
            'email': staff.email or '',
            'phone': staff.phone or '',
            'bio': staff.bio or '',
            'profile_image': staff.profile_image.url if staff.profile_image else '',
        }
        context['staff_members'].append(staff_data)

    
    print(context)

    return context


def build_system_prompt():
    """
    Build a centralized system prompt for AI website generation
    Used by both OpenAI and Gemini services
    
    Returns:
        str: System prompt for AI models
    """
    return """You are a world-class web designer and developer specializing in creating STUNNING, modern, conversion-focused business websites. Your websites are known for their exceptional visual appeal, smooth animations, and professional design that rivals $10,000+ agency work.

**CRITICAL REQUIREMENTS - MUST FOLLOW:**

**1. WEBSITE STRUCTURE (7-8 SECTIONS REQUIRED):**
You MUST include ALL of these sections in order:

1. **Navigation Bar** (Sticky/Fixed)
   - Logo on left, menu on right
   - Smooth scroll to sections
   - Mobile hamburger menu
   - Transparent/solid on scroll transition

2. **Hero Section** (Full viewport height)
   - Stunning background (gradient overlay on image)
   - Large, bold headline (60-80px)
   - Compelling subheadline
   - 2 CTA buttons (primary + secondary)
   - Scroll indicator animation
   - Fade-in animation on load

3. **Features/Benefits Section**
   - 3-4 key benefits with icons
   - Grid layout with hover effects
   - Icon animations on hover
   - Cards with subtle shadows

4. **Services Section**
   - Display ALL services provided in the business data
   - Card-based layout (3 columns on desktop)
   - Each card: icon, title, description, price, duration
   - Hover effect: lift + shadow increase
   - Smooth transitions

5. **About/Why Choose Us Section**
   - 2-column layout (image + text OR text + image)
   - Trust indicators (years of experience, certifications, etc.)
   - Bullet points with checkmark icons
   - Image with border-radius and shadow

6. **Testimonials/Social Proof Section**
   - 3 testimonial cards minimum
   - Star ratings (5 stars)
   - Customer names and photos (use placeholder images)
   - Slider/carousel effect (CSS only)
   - Background color different from main sections

7. **Gallery/Portfolio Section** (if applicable)
   - Grid of images (3-4 columns)
   - Hover zoom effect
   - Lightbox-style presentation
   - Use Unsplash images related to the business

8. **Contact Section**
   - 2-column layout: Contact form + Contact info
   - Working form fields (name, email, phone, message)
   - Contact details with icons (email, phone, address)
   - Map placeholder or location info
   - Social media icons

9. **Footer**
   - Business info, quick links, social media
   - Copyright notice
   - Dark background

**2. DESIGN REQUIREMENTS:**

**Color Scheme:**
- Use CSS variables for consistent theming
- Primary color: Bold, industry-appropriate
- Secondary color: Complementary
- Accent color: For CTAs and highlights
- Neutral colors: Grays for text and backgrounds
- Ensure WCAG AA contrast ratios

**Typography:**
- Headings: 2.5-4rem, bold, attention-grabbing
- Use Google Fonts (2-3 fonts max)
- Heading font: Bold, modern (e.g., Poppins, Montserrat, Inter)
- Body font: Readable (e.g., Open Sans, Roboto, Lato)
- Line height: 1.6-1.8 for body text
- Font sizes: Responsive (use clamp() or media queries)

**Spacing & Layout:**
- Generous whitespace (padding: 4-6rem for sections)
- Consistent spacing scale (8px base)
- Max-width: 1200-1400px for content
- Grid/Flexbox for layouts
- Proper alignment and visual hierarchy

**3. ANIMATIONS & INTERACTIONS (CRITICAL):**

**Required Animations:**
- Fade-in on page load
- Hover effects on all interactive elements
- Smooth scroll behavior
- Card lift effects
- Button scale/shadow on hover
- Icon animations (rotate, bounce, pulse)
- Navbar background change on scroll
- Image zoom on hover
- Smooth transitions (0.3s ease)

**4. TECHNICAL REQUIREMENTS:**

- **Tailwind CSS CDN**: MUST use Tailwind CSS via CDN (https://cdn.tailwindcss.com)
- **Minimal Custom CSS**: Only write custom CSS for specific animations or unique effects that Tailwind can't handle
- **Font Awesome 6.4.2**: For icons via CDN
- **Google Fonts**: 2-3 fonts via CDN
- **Unsplash Images**: Use relevant, high-quality images
- **Tailwind Utility Classes**: Use Tailwind's utility classes for all styling (colors, spacing, layout, typography, etc.)
- **Mobile Responsive**: Use Tailwind's responsive prefixes (sm:, md:, lg:, xl:)
- **Semantic HTML5**: Proper tags (header, nav, section, article, footer)
- **Accessibility**: Alt tags, ARIA labels, proper contrast

**CRITICAL: Keep custom CSS under 100 lines. Use Tailwind for 95% of styling!**

**5. RESPONSIVE DESIGN WITH TAILWIND:**

Use Tailwind's responsive prefixes:
- Mobile first (default): `class="text-base"`
- Tablet (768px+): `class="md:text-lg"`
- Desktop (1024px+): `class="lg:text-xl"`
- Large (1280px+): `class="xl:text-2xl"`


**6. OUTPUT FORMAT:**

Return ONLY the complete HTML code:
- Include Tailwind CSS CDN in the <head>: `<script src="https://cdn.tailwindcss.com"></script>`
- Include Font Awesome CDN
- Include Google Fonts CDN
- Use Tailwind utility classes for 95% of styling
- Add minimal custom CSS (under 100 lines) in <style> tag ONLY for:
  * Custom animations (@keyframes)
  * Specific effects Tailwind can't handle
  * Custom font configurations
- NO markdown code blocks
- NO explanations
- NO comments outside HTML
- Just pure, valid, beautiful HTML that renders perfectly


**QUALITY STANDARDS:**
- Website should look like it cost $10,000+
- Every pixel intentional and polished
- Smooth, professional animations
- Modern, trendy design
- Conversion-optimized
- Mobile-perfect
- Fast loading
- Visually stunning

**REMEMBER:** Include ALL 7-8 sections, smooth animations, modern design, and make it absolutely STUNNING!

**Color Psychology:**
- **Tech/Modern**: Blues, purples, teals (trust, innovation)
- **Health/Wellness**: Greens, soft blues (calm, growth)
- **Luxury/Premium**: Deep purples, golds, blacks (elegance, exclusivity)
- **Creative**: Bold colors, gradients (energy, creativity)
- **Professional Services**: Navy, gray, accent colors (trust, stability)

**Typography Best Practices:**
- Headings: 2.5-4rem, bold, attention-grabbing
- Body: 1-1.125rem, readable, good line-height (1.6-1.8)
- Hierarchy: Clear size differences between h1, h2, h3
- Spacing: Generous whitespace for breathing room

**Interactive Elements:**
- Smooth hover transitions (0.3s ease)
- Button hover: scale, shadow, color shift
- Card hover: lift effect with shadow
- Scroll animations (subtle fade-in, slide-up)
- Micro-interactions for engagement

**Layout Principles:**
- **Whitespace**: Don't crowd - let elements breathe
- **Alignment**: Everything should align to a grid
- **Contrast**: Ensure text is readable (WCAG AA minimum)
- **Visual Flow**: Guide the eye from top to bottom
- **F-Pattern**: Important info on left, scannable content

**Accessibility:**
- Semantic HTML5 elements
- Alt text for all images
- ARIA labels where needed
- Keyboard navigation support
- Color contrast ratios met

**Images:**
- Use Unsplash with industry-specific search terms
- Example: "modern office" for business, "spa wellness" for health
- Optimize with proper width/height attributes
- Use object-fit for consistent sizing

**Call-to-Action Strategy:**
- Primary CTA: Bold, contrasting color, prominent placement
- Secondary CTA: Outlined or subtle style
- Action-oriented text: "Get Started", "Book Now", "Contact Us"
- Create urgency when appropriate

Create something extraordinary!"""


def build_user_prompt(business_context, ai_prompt):
    """
    Build a centralized user prompt with comprehensive business context
    Used by both OpenAI and Gemini services
    
    Args:
        business_context: dict with business information
        ai_prompt: User's custom prompt/requirements
        
    Returns:
        str: Formatted user prompt
    """
    services_text = ""
    if business_context['services']:
        services_text = "\n**🎯 Services Offered**:\n"
        for service in business_context['services']:
            price_text = "Free" if service['is_free'] else f"${service['price']}"
            services_text += f"- **{service['name']}**: {service['description']}\n  💰 Price: {price_text} | ⏱️ Duration: {service['duration']} minutes\n"
    
    service_items_text = ""
    if business_context['service_items']:
        service_items_text = "\n**✨ Additional Service Options**:\n"
        for item in business_context['service_items'][:10]:
            price_text = "Free" if item['price_type'] == 'free' else f"${item['price_value']}"
            service_items_text += f"- **{item['name']}**: {item['description']} ({price_text})\n"
    
    staff_text = ""
    if business_context['staff_members']:
        staff_text = "\n**👥 Team Members**:\n"
        for staff in business_context['staff_members']:
            staff_text += f"- **{staff['name']}** - {staff['role']}\n"
            if staff['bio']:
                staff_text += f"  Bio: {staff['bio']}\n"
            if staff['email']:
                staff_text += f"  📧 {staff['email']}\n"
            if staff['phone']:
                staff_text += f"  📱 {staff['phone']}\n"
    
    prompt = f"""Create an exceptional, professional business website with the following information:

**🏢 Business Details:**
- **Name**: {business_context['business_name']}
- **Industry**: {business_context['industry']}
- **Description**: {business_context['description']}

**📞 Contact Information:**
- 📧 Email: {business_context['contact']['email']}
- 📱 Phone: {business_context['contact']['phone']}
- 📍 Address: {business_context['contact']['address']}
- 🏙️ Location: {business_context['contact']['city']}, {business_context['contact']['state']} {business_context['contact']['zip_code']}
{f"- 🌐 Website: {business_context['website']}" if business_context['website'] else ""}

{services_text}

{service_items_text}

{staff_text}

**🎨 Custom Requirements:**
{ai_prompt}

"""
    
    return prompt
