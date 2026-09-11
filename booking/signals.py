"""
Signals for the horilla_booking app.

booking_submitted — fired by PublicBookingView after a Booking is saved.
Receivers in horilla_crm.leads handle Lead/Contact/Activity creation.

Signal kwargs:
    booker_name     (str)     — full name entered by visitor
    booker_email    (str)     — email entered by visitor
    booking_instance (Booking) — the freshly saved Booking object
    company         (Company | None) — company derived from the BookingPage
"""

from django.dispatch import Signal

booking_submitted = Signal()
