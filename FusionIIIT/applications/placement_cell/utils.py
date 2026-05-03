"""
utils.py — placement_cell
Shared utility helpers used across views and services.

T02 / S11 / S35 / R08: Centralised pagination utility replacing the
30+ identical inline pagination blocks that existed in views.py.
"""
from django.core.paginator import Paginator

# T12 / S35: Named constants instead of magic numbers
PAGE_SIZE = 30
PAGE_WINDOW = 3


def paginate_queryset(qs, request, page_key='page', per_page=PAGE_SIZE):
    """
    Paginate *qs* and return a dict ready to merge into a template context.

    Returns
    -------
    dict with keys:
        page_obj       – current page object (or the original qs if no pagination)
        paginator      – Paginator instance (or '' when not paginated)
        page_range     – range of page numbers to display
        is_disabled    – flag for hiding previous-button at page 5+
        is_paginated   – bool, True when total > per_page
    """
    total = qs.count() if hasattr(qs, 'count') else len(qs)

    if total <= per_page:
        return {
            'page_obj': qs,
            'paginator': '',
            'page_range': '',
            'is_disabled': 0,
            'is_paginated': False,
        }

    paginator = Paginator(qs, per_page)
    page = request.GET.get(page_key, 1)
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1

    page_obj = paginator.page(page)
    total_page = page + PAGE_WINDOW
    is_disabled = 0

    if page < (paginator.num_pages - PAGE_WINDOW):
        if total <= per_page * 2:
            page_range = range(1, 3)
        else:
            page_range = range(1, total_page + 1)
        if page >= 5:
            is_disabled = 1
            page_range = range(page - 2, total_page)
    else:
        if page >= 5:
            is_disabled = 1
            page_range = range(page - 2, paginator.num_pages + 1)
        else:
            page_range = range(1, paginator.num_pages + 1)

    return {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_range': page_range,
        'is_disabled': is_disabled,
        'is_paginated': True,
    }
