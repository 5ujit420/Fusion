from datetime import datetime, timedelta

from django.test import SimpleTestCase

from applications.complaint_system.services import (
    get_complaint_finish_date,
    get_designation_name_for_location,
)


class ComplaintSystemServicesTest(SimpleTestCase):
    def test_get_complaint_finish_date_default(self):
        expected = (datetime.now() + timedelta(days=2)).date()
        result = get_complaint_finish_date('')
        self.assertEqual(result, expected)

    def test_get_complaint_finish_date_electricity(self):
        expected = (datetime.now() + timedelta(days=2)).date()
        result = get_complaint_finish_date('Electricity')
        self.assertEqual(result, expected)

    def test_get_complaint_finish_date_internet(self):
        expected = (datetime.now() + timedelta(days=4)).date()
        result = get_complaint_finish_date('Internet')
        self.assertEqual(result, expected)

    def test_get_designation_name_for_location_known(self):
        self.assertEqual(get_designation_name_for_location('hall-3'), 'hall3caretaker')
        self.assertEqual(get_designation_name_for_location('CC1'), 'cc1convener')

    def test_get_designation_name_for_location_default(self):
        self.assertEqual(get_designation_name_for_location('unknown'), 'rewacaretaker')
