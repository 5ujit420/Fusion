# exceptions.py
# Domain exceptions for the visitor_hostel module.
# T-15: Typed exceptions replace silent bare-except swallowing.


class BookingError(Exception):
    """Raised by services when a booking operation violates a business rule."""
    pass


class InventoryError(Exception):
    """Raised by services when an inventory operation violates a business rule."""
    pass
