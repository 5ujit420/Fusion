import datetime
from django.utils import timezone
from applications.filetracking.sdk.methods import forward_file
from applications.filetracking.models import File
from notification.views import complaint_system_notif

from .models import StudentComplain, Caretaker
from . import selectors


def lodge_complaint(user, complainer_extra_info, data: dict) -> StudentComplain:
    """
    Lodges a new complaint, calculates the deadline based on type,
    finds the responsible caretaker for the area, and sends a notification.
    Consolidates identical logic from UserComplaintView, CaretakerLodgeView, ServiceProviderLodgeView.
    """
    data['complainer'] = complainer_extra_info
    data['status'] = 0

    comp_type = data.get('complaint_type', '')
    
    # Finish time calculation exactly as per original logic
    now_date = datetime.datetime.now()
    if comp_type == 'Electricity':
        complaint_finish = now_date + datetime.timedelta(days=2)
    elif comp_type == 'carpenter':
        complaint_finish = now_date + datetime.timedelta(days=2)
    elif comp_type == 'plumber':
        complaint_finish = now_date + datetime.timedelta(days=2)
    elif comp_type == 'garbage':
        complaint_finish = now_date + datetime.timedelta(days=1)
    elif comp_type == 'dustbin':
        complaint_finish = now_date + datetime.timedelta(days=1)
    elif comp_type == 'internet':
        complaint_finish = now_date + datetime.timedelta(days=4)
    elif comp_type == 'other':
        complaint_finish = now_date + datetime.timedelta(days=3)
    else:
        # Default fallback mapped to original empty handling
        complaint_finish = now_date + datetime.timedelta(days=2)
        
    data['complaint_finish'] = complaint_finish.date()

    # Create the complaint directly via ORM 
    # (Serializer validated data is passed in 'data' dictionary)
    complaint = StudentComplain.objects.create(**data)

    location = data.get('location', '')
    if location == "hall-1":
        dsgn = "hall1caretaker"
    elif location == "hall-3":
        dsgn = "hall3caretaker"
    elif location == "hall-4":
        dsgn = "hall4caretaker"
    elif location == "CC1":
        dsgn = "cc1convener"
    elif location == "CC2":
        dsgn = "CC2 convener"
    elif location == "core_lab":
        dsgn = "corelabcaretaker"
    elif location == "LHTC":
        dsgn = "lhtccaretaker"
    elif location == "NR2":
        dsgn = "nr2caretaker"
    elif location == "Maa Saraswati Hostel":
        dsgn = "mshcaretaker"
    elif location == "Nagarjun Hostel":
        dsgn = "nhcaretaker"
    elif location == "Panini Hostel":
        dsgn = "phcaretaker"
    else:
        dsgn = "rewacaretaker"
    
    caretakers_designations = selectors.get_holds_designations_by_name(dsgn)

    student = 1
    message = "A New Complaint has been lodged"
    
    for caretaker_dsg in caretakers_designations:
        complaint_system_notif(user, caretaker_dsg.user, 'lodge_comp_alert', complaint.id, student, message)
        
    return complaint


def submit_caretaker_feedback(caretaker_type: str, rating: int, feedback: str):
    """
    Submits blanket feedback for a specific type of caretaker (area),
    updating the rating rolling average.
    """
    all_caretaker = selectors.get_caretakers_by_area(caretaker_type)
    for caretaker in all_caretaker:
        rate = caretaker.rating
        if rate == 0:
            newrate = rating
        else:
            newrate = (rate + rating) / 2
        caretaker.myfeedback = feedback
        caretaker.rating = newrate
        caretaker.save()


def submit_complaint_feedback(complaint: StudentComplain, rating: int, feedback: str):
    """
    Submits feedback specifically tied to a single complaint and recalculates
    the assigned caretaker's rating.
    Consolidates identical mathematical logic from 4 separate endpoints.
    """
    complaint.feedback = feedback
    complaint.flag = rating
    complaint.save()

    caretaker = selectors.get_caretaker_by_location(complaint.location)
    if caretaker:
        rate = caretaker.rating
        if rate == 0:
            newrate = rating
        else:
            newrate = int((rating + rate) / 2)
        caretaker.rating = newrate
        caretaker.save()


def resolve_complaint(user, complaint: StudentComplain, status_yes_no: str, comment: str, upload_resolved=None):
    """
    Resolves a complaint, updating the status, generating a notification to the complainer,
    and handling optional resolution proof images.
    Consolidates logic mapped across caretakers and service providers.
    """
    intstatus = 2 if status_yes_no == 'Yes' else 3
    complaint.status = intstatus
    complaint.comment = comment

    if upload_resolved:
        complaint.upload_resolved = upload_resolved

    complaint.save()

    student = 0
    if status_yes_no == 'Yes':
        message = "Congrats! Your complaint has been resolved"
        notification_type = 'comp_resolved_alert'
    else:
        message = "Your complaint has been declined"
        notification_type = 'comp_declined_alert'

    complaint_system_notif(user, complaint.complainer.user, notification_type,
                            complaint.id, student, message)
    return complaint


def assign_worker_to_complaint(request_user, complaint: StudentComplain):
    """
    Assigns the correct service_provider for the complaint, forwards any attached files,
    and updates the complaint status. Extracts tight filetracking SDK coupling from View layer.
    """
    complaint_type = complaint.complaint_type
    
    # Get the service provider for this complaint type
    service_providers = selectors.get_service_providers_by_type(complaint_type)
    if not service_providers.exists():
        raise ValueError('ServiceProvider does not exist for this complaint type')
        
    service_provider = service_providers.first()
    service_provider_details = selectors.get_extrainfo_by_id(service_provider.ser_pro_id.id)
    
    # Update status mapping
    complaint.status = 1
    complaint.save()

    # Get designations for provider
    sup_designations = selectors.get_holds_designations_by_user(service_provider_details.user_id)
    
    # Notify providers
    for sup in sup_designations:
        provider_user = selectors.get_user_by_username(sup.user.username)
        complaint_system_notif(
            request_user, provider_user, 'comp_assigned_alert', 
            complaint.id, 0, "A new complaint has been assigned to you"
        )
        
    # Forward the file attachment
    files = selectors.get_files_for_complaint(complaint.id)
    
    if files.exists():
        service_provider_username = selectors.get_user_by_username(service_provider_details.user.username).username

        # This SDK call remains pure to its origin scope inside a service function
        forward_file(
            file_id=files.first().id,
            receiver=service_provider_username,
            receiver_designation=sup_designations.first().designation,
            file_extra_JSON={},
            remarks="",
            file_attachment=None
        )

    return complaint


def remove_worker(worker):
    """
    Removes a worker as long as they aren't assigned to any open complaints.
    """
    assigned_complaints = selectors.get_assigned_complaints_count_for_worker(worker)
    if assigned_complaints == 0:
        worker.delete()
        return True
    return False

def change_complaint_status(complaint: StudentComplain, status_str: str):
    """
    Arbitrary change status, unassigning workers if declined or resolved.
    """
    status_int = int(status_str)
    if status_int in (2, 3):
        complaint.status = status_int
        complaint.worker_id = None
    else:
        complaint.status = status_int
    complaint.save()
    return complaint
