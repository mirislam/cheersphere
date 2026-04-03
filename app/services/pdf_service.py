import io
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import os

def to_pdt(dt):
    import zoneinfo
    from datetime import timezone
    if not dt: return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(zoneinfo.ZoneInfo("America/Los_Angeles")).strftime('%b %d, %Y %I:%M %p')

def generate_event_pdf(request, event, messages):
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'pdf')
    env = Environment(loader=FileSystemLoader(template_dir))
    env.filters['pdt'] = to_pdt
    template = env.get_template('event_pdf.html')
    
    html_out = template.render(event=event, messages=messages)
    
    pdf_buffer = io.BytesIO()
    HTML(string=html_out, base_url=str(request.base_url)).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    
    return pdf_buffer
