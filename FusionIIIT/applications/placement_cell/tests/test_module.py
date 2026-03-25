
from django.test import TestCase
from applications.placement_cell.models import (
    PlacementRecord, Role, ChairmanVisit, PlacementSchedule, NotifyStudent
)
from applications.placement_cell.services import (
    save_placement_record, save_placement_schedule, save_chairman_visit
)

class PlacementCellServicesTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(role="developer")
        
    def test_save_placement_record(self):
        data = {
            'placement_type': 'PLACEMENT',
            'student_name': 'Test Student',
            'ctc': '10 LPA',
            'year': '2025',
            'test_type': 'Written',
            'test_score': '90'
        }
        record = save_placement_record(data)
        self.assertEqual(record.name, 'Test Student')
        self.assertEqual(record.ctc, '10 LPA')
        self.assertEqual(PlacementRecord.objects.count(), 1)

    def test_save_chairman_visit(self):
        data = {
            'company_name': 'Test Company',
            'location': 'Test Location',
            'date': '2025-01-01',
            'description': 'Test Description',
            'timestamp': '2025-01-01T00:00:00Z'
        }
        visit = save_chairman_visit(data)
        self.assertEqual(visit.company_name, 'Test Company')
        self.assertEqual(ChairmanVisit.objects.count(), 1)

    def test_save_placement_schedule(self):
        data = {
            'placement_type': 'PLACEMENT',
            'company_name': 'Test Company',
            'description': 'Test Description',
            'ctc': '10 LPA',
            'time_stamp': '2025-01-01T00:00:00Z',
            'title': 'Test Title',
            'placement_date': '2025-01-01',
            'resume': 'resume.pdf',
            'role': 'developer',
            'location': 'Test Location',
            'schedule_at': '10:00 AM'
        }
        schedule = save_placement_schedule(data)
        self.assertEqual(schedule.title, 'Test Title')
        self.assertEqual(schedule.role.role, 'developer')
        self.assertEqual(PlacementSchedule.objects.count(), 1)
        self.assertEqual(NotifyStudent.objects.count(), 1)
