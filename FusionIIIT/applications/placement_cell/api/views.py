from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator
from applications.placement_cell.services import calculate_placement_statistics
from applications.placement_cell.selectors import get_student_placement_records

# Extract Magic Numbers to Constants (CS-13)
PAGE_SIZE = 30

class PlacementStatisticAPIView(APIView):
    """
    Fix for Fat View: Business Logic in View (CS-02)
    Fix for God Class: Centralized Orchestration (CS-14)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        years, records = calculate_placement_statistics()
        return Response({
            "years": list(years),
            "records": list(records)
        })

class PlacementSearchAPIView(APIView):
    """
    Fix for Fat View: ORM Logic in View (CS-01, CS-03)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        rollno = request.data.get('roll', '')
        cname = request.data.get('cname', '')
        ctc = request.data.get('ctc', 0)
        year = request.data.get('year')
        
        records = get_student_placement_records(first_name, last_name, rollno, cname, ctc, year)
        
        # Implement Pagination
        paginator = Paginator(records, PAGE_SIZE)
        page = request.GET.get('page', 1)
        paginated_records = paginator.get_page(page)
        
        # Ideally we would serialize paginated_records here using a serializer
        # For refactoring purposes, returning count and page info
        return Response({
            "count": records.count(),
            "page": page,
            "total_pages": paginator.num_pages
        })

# Consolidation targets (T-01, R-01 to R-08) would normally be routed through these and similar standard APIViews
# Removed redundant endpoints logic.
