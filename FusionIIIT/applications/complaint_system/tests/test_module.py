from django.test import TestCase, RequestFactory
from django.utils import timezone
from datetime import timedelta
import datetime

from applications.complaint_system.models import StudentComplain, Caretaker, AreaChoices, ComplaintTypeChoices
from applications.globals.models import ExtraInfo, User
from applications.complaint_system import services, selectors

class ComplaintSystemServicesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create user & extrainfo for complainer
        cls.user1 = User.objects.create_user(username='student1', password='password123')
        cls.extra1 = ExtraInfo.objects.create(
            id='2020000', user=cls.user1, user_type='student', department=None
        )

        # Create user & extrainfo for caretaker
        cls.user2 = User.objects.create_user(username='caretaker1', password='password123')
        cls.extra2 = ExtraInfo.objects.create(
            id='3030000', user=cls.user2, user_type='staff'
        )

        # Create Caretaker instance
        cls.caretaker = Caretaker.objects.create(
            staff_id=cls.extra2,
            area=AreaChoices.HALL_3,
            rating=0,
            myfeedback="new"
        )
        
    def test_lodge_complaint_creates_complaint_and_sets_deadline(self):
        """
        Tests the lodge_complaint service calculates SLAs correctly and saves via ORM.
        """
        data = {
             'complaint_type': ComplaintTypeChoices.ELECTRICITY,
             'location': AreaChoices.HALL_3,
             'details': 'Fan not working'
        }
        
        # Act
        complaint = services.lodge_complaint(user=self.user1, complainer_extra_info=self.extra1, data=data)
        
        # Assert
        self.assertEqual(complaint.complainer, self.extra1)
        self.assertEqual(complaint.location, AreaChoices.HALL_3)
        self.assertEqual(complaint.status, 0)
        
        # Math calculation assertion
        expected_date = (datetime.datetime.now() + datetime.timedelta(days=2)).date()
        self.assertEqual(complaint.complaint_finish, expected_date)

    def test_submit_complaint_feedback(self):
        """
        Tests mathematical tracking of Caretaker rating via feedback service.
        """
        data = {
             'complaint_type': ComplaintTypeChoices.ELECTRICITY,
             'location': AreaChoices.HALL_3,
             'details': 'Test 2'
        }
        complaint = services.lodge_complaint(user=self.user1, complainer_extra_info=self.extra1, data=data)
        
        # Action 1: First feedback
        services.submit_complaint_feedback(complaint, rating=4, feedback="Good")
        self.caretaker.refresh_from_db()
        self.assertEqual(self.caretaker.rating, 4)
        
        # Action 2: Second feedback
        complaint2 = services.lodge_complaint(user=self.user1, complainer_extra_info=self.extra1, data=data)
        services.submit_complaint_feedback(complaint2, rating=2, feedback="Bad")
        self.caretaker.refresh_from_db()
        # (4 + 2) / 2 = 3
        self.assertEqual(self.caretaker.rating, 3)

    def test_resolve_complaint_updates_status(self):
        """
        Tests the resolution functionality updating state natively.
        """
        data = {
             'complaint_type': ComplaintTypeChoices.ELECTRICITY,
             'location': AreaChoices.HALL_3,
             'details': 'Test 3'
        }
        complaint = services.lodge_complaint(user=self.user1, complainer_extra_info=self.extra1, data=data)
        
        # Accept resolve
        resolved = services.resolve_complaint(self.user1, complaint, 'Yes', 'Fixed')
        self.assertEqual(resolved.status, 2)
        
        # Decline resolve
        declined = services.resolve_complaint(self.user1, complaint, 'No', 'Not Fixed')
        self.assertEqual(declined.status, 3)

class ComplaintSystemSelectorsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test_user')
        cls.extra = ExtraInfo.objects.create(id="123", user=cls.user, user_type="student")
        
    def test_get_extrainfo_by_user(self):
        fetched = selectors.get_extrainfo_by_user(self.user)
        self.assertEqual(fetched, self.extra)

    def test_check_user_roles(self):
        roles = selectors.check_user_roles(self.extra)
        self.assertFalse(roles['is_caretaker'])
        self.assertFalse(roles['is_warden'])
        self.assertEqual(roles['user_type'], 'student')
