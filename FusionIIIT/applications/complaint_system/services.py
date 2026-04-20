import datetime
from datetime import datetime as dt, timedelta
from applications.globals.models import HoldsDesignation
from notification.views import complaint_system_notif
from .models import Caretaker, StudentComplain, AreaChoices, ComplaintTypeChoices

LOCATION_TO_DESIGNATION = {
    AreaChoices.HALL_1: "hall1caretaker",
    AreaChoices.HALL_3: "hall3caretaker",
    AreaChoices.HALL_4: "hall4caretaker",
    AreaChoices.LIBRARY: "cc1convener",
    AreaChoices.COMPUTER_CENTER: "CC2 convener",
    AreaChoices.CORE_LAB: "corelabcaretaker",
    AreaChoices.LHTC: "lhtccaretaker",
    AreaChoices.NR2: "nr2caretaker",
    AreaChoices.MAA_SARASWATI_HOSTEL: "mshcaretaker",
    AreaChoices.NAGARJUN_HOSTEL: "nhcaretaker",
    AreaChoices.PANINI_HOSTEL: "phcaretaker",
    AreaChoices.REWA_RESIDENCY: "rewacaretaker",
}

COMPLAINT_FINISH_DURATIONS = {
    ComplaintTypeChoices.ELECTRICITY: 2,
    ComplaintTypeChoices.CARPENTER: 2,
    ComplaintTypeChoices.PLUMBER: 2,
    ComplaintTypeChoices.GARBAGE: 1,
    ComplaintTypeChoices.DUSTBIN: 1,
    ComplaintTypeChoices.INTERNET: 4,
    ComplaintTypeChoices.OTHER: 3,
}

class ComplaintService:
    @staticmethod
    def get_finish_time(comp_type):
        days = COMPLAINT_FINISH_DURATIONS.get(comp_type, 3)
        return (dt.now() + timedelta(days=days)).date()

    @staticmethod
    def get_designation_for_location(location):
        return LOCATION_TO_DESIGNATION.get(location, "rewacaretaker")

    @staticmethod
    def lodge_complaint(user, complaint):
        location = complaint.location
        dsgn = ComplaintService.get_designation_for_location(location)
        caretakers = HoldsDesignation.objects.select_related('user', 'working', 'designation').filter(designation__name=dsgn).distinct('user')
        
        # Send notification to all relevant caretakers
        student = 1
        message = "A New Complaint has been lodged"
        for caretaker in caretakers:
            complaint_system_notif(user, caretaker.user, 'lodge_comp_alert', complaint.id, student, message)
        
        return True
        
    @staticmethod
    def resolve_complaint(complaint, newstatus, comment, request_user, upload_resolved=None):
        intstatus = 2 if newstatus == 'Yes' else 3
        complaint.status = intstatus
        complaint.comment = comment
        if upload_resolved:
            complaint.upload_resolved = upload_resolved
        complaint.save()

        # notification
        try:
            student = 0
            if newstatus == 'Yes':
                message = "Congrats! Your complaint has been resolved"
                notification_type = 'comp_resolved_alert'
            else:
                message = "Your complaint has been declined"
                notification_type = 'comp_declined_alert'

            complaint_system_notif(
                request_user, 
                complaint.complainer.user, 
                notification_type, 
                complaint.id, 
                student, 
                message
            )
        except Exception:
            pass
        return complaint

class RatingService:
    @staticmethod
    def update_caregiver_rating(location, rating):
        care = Caretaker.objects.filter(area=location).first()
        if care:
            rate = care.rating
            care.rating = int((rating + rate) / 2) if rate != 0 else rating
            care.save()
            return care
        return None
