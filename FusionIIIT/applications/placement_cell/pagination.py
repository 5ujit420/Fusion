from django.core.paginator import Paginator

def paginate_queryset(request, queryset, per_page=30):
    """Paginate a queryset and return (page_obj, page_range, paginator, pagination_flag, is_disabled).

    Keeps page-range logic compatible with existing code to avoid behavioral changes.
    """
    total_query = queryset.count() if hasattr(queryset, 'count') else len(queryset)
    if total_query > per_page:
        paginator = Paginator(queryset, per_page)
        page = request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page)
        except Exception:
            page_obj = paginator.page(1)
        page = int(page_obj.number)
        total_page = int(page + 3)

        if page < (paginator.num_pages - 3):
            if total_query > per_page and total_query <= (per_page * 2):
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

        return page_obj, page_range, paginator, 1, is_disabled
    else:
        return queryset, (), None, 0, 0
