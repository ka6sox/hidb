from numbers import Number
from decimal import Decimal

from jinja2.utils import markupsafe

def format_currency(value):
    if not isinstance(value, (Number, Decimal)):
        raise TypeError("Value must be Number.")
    if value < 0:
        return markupsafe.Markup('<span style="color:red">- </span>' + format_currency(-value))
    return "${:,.2f}".format(value)
