import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
from django.utils import timezone
from .models import Event
from .views import send_event_reminder_email

def generate_receipt_pdf(event, user, payment):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Set up the document
    p.setTitle(f"Receipt for {event.name}")

    # Add logo (replace with your actual logo path)
    # p.drawImage("path/to/your/logo.png", 50, height - 100, width=100, height=50)

    # Add title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Receipt for {event.name}")

    # Add event details
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"Date: {event.start_datetime.strftime('%B %d, %Y')}")
    p.drawString(50, height - 95, f"Time: {event.start_datetime.strftime('%I:%M %p')} - {event.end_datetime.strftime('%I:%M %p')}")
    p.drawString(50, height - 110, f"Location: {event.location_description}")

    # Add user details
    p.drawString(50, height - 140, f"Name: {user.get_full_name()}")
    p.drawString(50, height - 155, f"Email: {user.email}")

    # Add payment details
    p.drawString(50, height - 185, "Payment Details:")
    data = [
        ["Amount Paid", f"₹{payment.amount}"],
        ["Payment Date", payment.payment_date.strftime('%B %d, %Y')],
        ["Payment Method", payment.payment_method],
        ["Transaction ID", payment.payment_id],
        ["Status", payment.get_status_display()],
    ]
    table = Table(data, colWidths=[2*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 300)

    # Add footer
    p.setFont("Helvetica", 10)
    p.drawString(50, 50, "Thank you for your registration!")
    p.drawString(50, 35, f"Generated on: {datetime.now().strftime('%B %d, %Y %I:%M %p')}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer

def check_and_send_reminders():
    now = timezone.now()
    upcoming_events = Event.objects.filter(
        start_datetime__gt=now,
        start_datetime__lte=now + timezone.timedelta(days=1)
    )

    for event in upcoming_events:
        if event.should_send_reminder():
            send_event_reminder_email(event)
            event.last_reminder_sent = now
            event.save()
