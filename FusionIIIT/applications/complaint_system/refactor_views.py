import re

file_path = 'c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. CaretakerLodgeView.post and ServiceProviderLodgeView.post `complaint_finish` logic
comp_logic_pattern = re.compile(
    r'        comp_type = data\.get\("complaint_type", ""\)\n        # Finish time is according to complaint type\n        complaint_finish = datetime\.now\(\) \+ timedelta\(days=2\)\n        if comp_type == "Electricity":\n            complaint_finish = datetime\.now\(\) \+ timedelta\(days=2\)\n        elif comp_type == "Carpenter":\n            complaint_finish = datetime\.now\(\) \+ timedelta\(days=2\)\n        elif comp_type == "Plumber":\n            complaint_finish = datetime\.now\(\) \+ timedelta\(days=2\)\n        elif comp_type == "Garbage":\n            complaint_finish = datetime\.now\(\) \+ timedelta\(days=1\)\n        elif comp_type == "Dustbin":\n            complaint_finish = datetime\.now\(\) \+ timedelta\(days=1\)\n        elif comp_type == "Internet":\n            complaint_finish = datetime\.now\(\) \+ timedelta\(days=4\)\n        elif comp_type == "Other":\n            complaint_finish = datetime\.now\(\) \+ timedelta\(days=3\)\n        data\["complaint_finish"\] = complaint_finish\.date\(\)',
    re.DOTALL
)

replacement_comp_logic = r'''        
        from .services import ComplaintService
        data["complaint_finish"] = ComplaintService.get_finish_time(comp_type)'''

content = comp_logic_pattern.sub(replacement_comp_logic, content)

# 2. CaretakerLodgeView notification logic
loc_logic_pattern_1 = re.compile(
    r'            # Notification logic \(if any\)[\s\r\n]+location = data\.get\("location", ""\)[\s\r\n]+caretaker_name = Caretaker\.objects\.select_related\("staff_id", "staff_id__user"\)\.filter\(area=location\)\.first\(\)[\s\r\n]+student = 1[\s\r\n]+message = "A New Complaint has been lodged"[\s\r\n]+if caretaker_name:[\s\r\n]+complaint_system_notif\(request\.user, caretaker_name\.staff_id\.user, "lodge_comp_alert", complaint\.id, student, message\)',
    re.DOTALL
)
replacement_loc_logic_1 = r'''            ComplaintService.lodge_complaint(request.user, complaint)'''
content = loc_logic_pattern_1.sub(replacement_loc_logic_1, content)

loc_logic_pattern_2 = re.compile(
    r'            location = data\.get\("location", ""\)[\s\r\n]+worker_type = data\.get\("complaint_type", ""\)[\s\r\n]+dsgn = ""[\s\r\n]+if location == "hall-1":[\s\r\n]+dsgn = "hall1caretaker"[\s\r\n]+elif location == "hall-3":[\s\r\n]+dsgn = "hall3caretaker"[\s\r\n]+elif location == "hall-4":[\s\r\n]+dsgn = "hall4caretaker"[\s\r\n]+elif location == "CC1":[\s\r\n]+dsgn = "cc1convener"[\s\r\n]+elif location == "CC2":[\s\r\n]+dsgn = "CC2 convener"[\s\r\n]+elif location == "core_lab":[\s\r\n]+dsgn = "corelabcaretaker"[\s\r\n]+elif location == "LHTC":[\s\r\n]+dsgn = "lhtccaretaker"[\s\r\n]+elif location == "NR2":[\s\r\n]+dsgn = "nr2caretaker"[\s\r\n]+elif location == "Maa Saraswati Hostel":[\s\r\n]+dsgn = "mshcaretaker"[\s\r\n]+elif location == "Nagarjun Hostel":[\s\r\n]+dsgn = "nhcaretaker"[\s\r\n]+elif location == "Panini Hostel":[\s\r\n]+dsgn = "phcaretaker"[\s\r\n]+else:[\s\r\n]+dsgn = "rewacaretaker"[\s\r\n]*caretakers = HoldsDesignation\.objects\.select_related\("user", "working", "designation"\) \.filter\(designation__name=dsgn\)\.distinct\("user"\)[\s\r\n]*student = 1[\s\r\n]*message = "A New Complaint has been lodged"[\s\r\n]*for caretaker in caretakers:[\s\r\n]+complaint_system_notif\(request\.user, caretaker\.user, "lodge_comp_alert", complaint\.id, student, message\)',
    re.DOTALL
)
content = loc_logic_pattern_2.sub(replacement_loc_logic_1, content)


# 3. ResolvePendingView
resolve_logic_pattern = re.compile(
    r'            newstatus = serializer\.validated_data\["yesorno"\][\s\r\n]+comment = serializer\.validated_data\.get\("comment", ""\)[\s\r\n]+intstatus = 2 if newstatus == "Yes" else 3[\s\r\n]+StudentComplain\.objects\.filter\(id=cid\)\.update\(status=intstatus, comment=comment\)[\s\r\n]+# Send notification to the complainer[\s\r\n]+# ✅ Get the complaint record[\s\r\n]+try:[\s\r\n]+complaint = StudentComplain\.objects\.get\(id=cid\)[\s\r\n]+complaint\.status = intstatus[\s\r\n]+complaint\.comment = comment(?:[\s\r\n]+# ✅ Save the uploaded image if it exists[\s\r\n]+if "upload_resolved" in request\.FILES:[\s\r\n]+complaint\.upload_resolved = request\.FILES\["upload_resolved"\](?:[\s\r\n]+print\("✅ Image Saved:", complaint\.upload_resolved\))?)?[\s\r\n]+complaint\.save\(\)[\s\r\n]+# ✅ Send notification[\s\r\n]+complainer_details = StudentComplain\.objects\.select_related\("complainer"\)\.get\(id=cid\)[\s\r\n]+student = 0[\s\r\n]+if newstatus == "Yes":[\s\r\n]+message = "Congrats! Your complaint has been resolved"[\s\r\n]+notification_type = "comp_resolved_alert"[\s\r\n]+else:[\s\r\n]+message = "Your complaint has been declined"[\s\r\n]+notification_type = "comp_declined_alert"[\s\r\n]+complaint_system_notif\(request\.user, complainer_details\.complainer\.user, notification_type,[\s\r\n]+complainer_details\.id, student, message\)[\s\r\n]+return Response\(\{"success": "Complaint status updated"\}\)[\s\r\n]+except StudentComplain\.DoesNotExist:[\s\r\n]+return Response\(\{"error": "Complaint not found"\}, status=404\)',
    re.DOTALL
)

replacement_resolve_logic = r'''            newstatus = serializer.validated_data["yesorno"]
            comment = serializer.validated_data.get("comment", "")
            upload_resolved = request.FILES.get("upload_resolved", None)
            
            try:
                complaint = StudentComplain.objects.get(id=cid)
                from .services import ComplaintService
                ComplaintService.resolve_complaint(complaint, newstatus, comment, request.user, upload_resolved=upload_resolved)
                return Response({"success": "Complaint status updated"})
            except StudentComplain.DoesNotExist:
                return Response({"error": "Complaint not found"}, status=404)'''

content = resolve_logic_pattern.sub(replacement_resolve_logic, content)

# 4. Remove int(rating) redundant blocks from views
feedback_int_pattern = re.compile(
    r'        try:[\s\r\n]+rating = int\(rating\)[\s\r\n]+except ValueError:[\s\r\n]+return Response\(\{"error": "Invalid rating"\}, status=(?:status\.)?HTTP_400_BAD_REQUEST\)',
    re.DOTALL
)
content = feedback_int_pattern.sub(r'        ', content)
feedback_int_pattern_2 = re.compile(
    r'        try:[\s\r\n]+rating = int\(rating\)[\s\r\n]+except ValueError:[\s\r\n]+return Response\(\{"error": "Invalid rating"\}, status=400\)',
    re.DOTALL
)
content = feedback_int_pattern_2.sub(r'        ', content)


# 5. Generic replace for RatingService
rating_logic_1 = re.compile(
    r'            StudentComplain\.objects\.filter\(id=complaint_id\)\.update\(feedback=feedback, flag=rating\)[\s\r\n]+a = StudentComplain\.objects\.filter\(id=complaint_id\)\.first\(\)[\s\r\n]+care = Caretaker\.objects\.filter\(area=a\.location\)\.first\(\)[\s\r\n]+rate = care\.rating[\s\r\n]+if rate == 0:[\s\r\n]+newrate = rating[\s\r\n]+else:[\s\r\n]+newrate = int\(\(rating \+ rate\) / 2\)[\s\r\n]+care\.rating = newrate[\s\r\n]+care\.save\(\)',
    re.DOTALL
)
replacement_rating_1 = r'''            StudentComplain.objects.filter(id=complaint_id).update(feedback=feedback, flag=rating)
            a = StudentComplain.objects.filter(id=complaint_id).first()
            if a:
                from .services import RatingService
                RatingService.update_caregiver_rating(a.location, rating)'''
content = rating_logic_1.sub(replacement_rating_1, content)

rating_logic_2 = re.compile(
    r'            StudentComplain\.objects\.filter\(id=complaint_id\)\.update\(feedback=feedback, flag=rating\)[\s\r\n]+a = StudentComplain\.objects\.select_related\("complainer", "complainer__user", "complainer__department"\)\.filter\(id=complaint_id\)\.first\(\)[\s\r\n]+care = Caretaker\.objects\.filter\(area=a\.location\)\.first\(\)[\s\r\n]+rate = care\.rating[\s\r\n]+if rate == 0:[\s\r\n]+newrate = rating[\s\r\n]+else:[\s\r\n]+newrate = int\(\(rating \+ rate\) / 2\)[\s\r\n]+care\.rating = newrate[\s\r\n]+care\.save\(\)',
    re.DOTALL
)
replacement_rating_2 = r'''            StudentComplain.objects.filter(id=complaint_id).update(feedback=feedback, flag=rating)
            a = StudentComplain.objects.select_related("complainer", "complainer__user", "complainer__department").filter(id=complaint_id).first()
            if a:
                from .services import RatingService
                RatingService.update_caregiver_rating(a.location, rating)'''
content = rating_logic_2.sub(replacement_rating_2, content)

rating_logic_3 = re.compile(
    r'            StudentComplain\.objects\.filter\(id=complaint_id\)\.update\(feedback=feedback, flag=rating\)[\s\r\n]+# Update caretaker\'s rating[\s\r\n]+try:[\s\r\n]+complaint = StudentComplain\.objects\.select_related\("complainer", "complainer__user", "complainer__department"\)\.get\(id=complaint_id\)[\s\r\n]+caretaker = Caretaker\.objects\.get\(area=complaint\.location\)[\s\r\n]+rate = caretaker\.rating[\s\r\n]+if rate == 0:[\s\r\n]+newrate = rating[\s\r\n]+else:[\s\r\n]+newrate = int\(\(rating \+ rate\) / 2\)[\s\r\n]+caretaker\.rating = newrate[\s\r\n]+caretaker\.save\(\)[\s\r\n]+return Response\(\{"success": "Feedback submitted"\}\)[\s\r\n]+except Caretaker\.DoesNotExist:[\s\r\n]+return Response\(\{"error": "Caretaker not found"\}, status=status\.HTTP_404_NOT_FOUND\)',
    re.DOTALL
)
replacement_rating_3 = r'''            StudentComplain.objects.filter(id=complaint_id).update(feedback=feedback, flag=rating)
            complaint = StudentComplain.objects.select_related("complainer", "complainer__user", "complainer__department").filter(id=complaint_id).first()
            if complaint:
                from .services import RatingService
                RatingService.update_caregiver_rating(complaint.location, rating)
            return Response({"success": "Feedback submitted"})'''
content = rating_logic_3.sub(replacement_rating_3, content)


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
