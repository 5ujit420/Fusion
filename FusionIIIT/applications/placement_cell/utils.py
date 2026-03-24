"""
Utilities for placement_cell module.

Contains shared pagination, PDF rendering, and Excel export utilities.

Audit refs: R05, S49, S50
"""
from html import escape
from io import BytesIO

import xlwt
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


# ---------------------------------------------------------------------------
# Pagination utility  (R05 — replaces 15+ copy-pasted pagination blocks)
# ---------------------------------------------------------------------------

def paginate_queryset(queryset, request, page_size=30, page_param='page'):
    """
    Paginate a queryset and return pagination context.

    Returns a dict with:
        - queryset: the paginated page object (or original if < page_size)
        - page_range: range for template pagination links
        - paginator: Paginator object (or '')
        - is_disabled: whether to disable "first pages" link
        - has_pagination: 1 if paginated, 0 if not
        - total_count: total number of items

    Preserves the exact original pagination logic from views.py.
    """
    total_count = 0
    if queryset and queryset != '':
        try:
            total_count = queryset.count()
        except (TypeError, AttributeError):
            total_count = 0

    if total_count <= page_size:
        return {
            'queryset': queryset,
            'page_range': '',
            'paginator': '',
            'is_disabled': 0,
            'has_pagination': 0,
            'total_count': total_count,
        }

    paginator = Paginator(queryset, page_size)
    page = request.GET.get(page_param, 1)
    paginated_qs = paginator.page(page)
    page = int(page)
    total_page = int(page + 3)
    is_disabled = 0
    page_range = ''

    if page < (paginator.num_pages - 3):
        if total_count > page_size and total_count <= page_size * 2:
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
        'queryset': paginated_qs,
        'page_range': page_range,
        'paginator': paginator,
        'is_disabled': is_disabled,
        'has_pagination': 1,
        'total_count': total_count,
    }


# ---------------------------------------------------------------------------
# PDF rendering  (S49 — moved from views.py)
# ---------------------------------------------------------------------------

def render_to_pdf(template_src, context_dict):
    """Render an HTML template to PDF and return as HttpResponse.

    Preserves original logic from views.py render_to_pdf().
    """
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('We had some errors<pre>%s</pre>' % escape(html))


# ---------------------------------------------------------------------------
# Excel export  (S50 — moved from views.py)
# ---------------------------------------------------------------------------

def export_to_xls_std_records(qs):
    """Export student records to XLS format.

    Preserves original logic from views.py export_to_xls_std_records().
    """
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="report.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Report')

    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Roll No.', 'Name', 'CPI', 'Department', 'Discipline', 'Placed', 'Debarred']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    for student in qs:
        row_num += 1

        row = []
        row.append(student.id.id)
        row.append(student.id.user.first_name + ' ' + student.id.user.last_name)
        row.append(student.cpi)
        row.append(student.programme)
        row.append(student.id.department.name)
        if student.studentplacement.placed_type == "PLACED":
            row.append('Yes')
        else:
            row.append('No')
        if student.studentplacement.placed_type == "DEBAR":
            row.append('Yes')
        else:
            row.append('No')

        for col_num in range(len(row)):
            ws.write(row_num, col_num, row[col_num], font_style)

    wb.save(response)
    return response


def export_to_xls_invitation_status(qs):
    """Export invitation status records to XLS format.

    Preserves original logic from views.py export_to_xls_invitation_status().
    """
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="report.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Report')

    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Roll No.', 'Name', 'Company', 'CTC', 'Status']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    for student in qs:
        row_num += 1

        row = []
        row.append(student.unique_id.id.id)
        row.append(student.unique_id.id.user.first_name + ' ' + student.unique_id.id.user.last_name)
        row.append(student.notify_id.company_name)
        row.append(student.notify_id.ctc)
        row.append(student.invitation)

        for col_num in range(len(row)):
            ws.write(row_num, col_num, row[col_num], font_style)

    wb.save(response)
    return response
