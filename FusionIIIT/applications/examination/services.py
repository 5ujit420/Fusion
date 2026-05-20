import csv
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.db import transaction
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from applications.academic_procedures.models import course_registration
from applications.academic_information.models import Student
from applications.online_cms.models import Student_grades
from applications.academic_procedures.models import course_registration, Semester
from applications.programme_curriculum.models import (
    Batch,
    Course as Courses,
    CourseInstructor,
    CourseSlot,
    Discipline,
)

from .models import hidden_grades


def save_hidden_grades_batch(student_ids, semester_ids, course_ids, grades):
    saved_hidden_grades = []
    for student_id, semester_id, course_id, grade in zip(
        student_ids,
        semester_ids,
        course_ids,
        grades,
    ):
        hidden_grade, _ = hidden_grades.objects.update_or_create(
            course_id=course_id,
            student_id=student_id,
            semester_id=semester_id,
            defaults={
                'grade': grade,
            },
        )
        saved_hidden_grades.append(hidden_grade)
    return saved_hidden_grades


def import_grades_csv(csv_file, course_id, academic_year):
    decoded_file = csv_file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)

    required_columns = ['roll_no', 'grade', 'remarks']
    if not all(column in reader.fieldnames for column in required_columns):
        raise ValueError('CSV file must contain the following columns: roll_no, grade, remarks.')

    courses_info = Courses.objects.get(id=course_id)

    for row in reader:
        roll_no = row['roll_no']
        grade = row['grade']
        remarks = row['remarks']
        semester = row['semester'] if 'semester' in row and row['semester'] else None
        stud = Student.objects.get(id_id=roll_no)
        semester = semester or stud.curr_semester_no
        batch = stud.batch
        reSubmit = False

        Student_grades.objects.update_or_create(
            roll_no=roll_no,
            course_id_id=course_id,
            year=academic_year,
            semester=semester,
            batch=batch,
            defaults={
                'grade': grade,
                'remarks': remarks,
                'reSubmit': reSubmit,
            },
        )


def build_grade_pdf_bytes(course_id, academic_year, instructor_name, instructor_username):
    course_info = Courses.objects.get(id=course_id)
    grades = Student_grades.objects.filter(course_id_id=course_id, year=academic_year).order_by('roll_no')
    course = CourseInstructor.objects.filter(
        course_id_id=course_id,
        year=academic_year,
        instructor_id_id=instructor_username,
    )
    if not course:
        raise ValueError('course not found.')

    semester = course.first().semester_no

    all_grades = ['O', 'A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F', 'I', 'S', 'X']
    grade_counts = {grade: grades.filter(grade=grade).count() for grade in all_grades}

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    instructor = instructor_name
    styles = get_sample_pdf_styles()

    elements.append(Paragraph('Grade Sheet', styles['HeaderStyle']))
    field_label_style = styles['FieldLabelStyle']

    elements.append(Paragraph(f'<b>Session:</b> {academic_year}', field_label_style))
    elements.append(Paragraph(f'<b>Semester:</b> {semester}', field_label_style))
    elements.append(Paragraph(f'<b>Course Code:</b> {course_info.code}', field_label_style))
    elements.append(Paragraph(f'<b>Course Name:</b> {course_info.name}', field_label_style))
    elements.append(Paragraph(f'<b>Instructor:</b> {instructor}', field_label_style))

    data = [['S.No.', 'Roll Number', 'Grade']]
    for i, grade in enumerate(grades, 1):
        data.append([i, grade.roll_no, grade.grade])
    table = Table(data, colWidths=[80, 300, 100])
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E0E0E0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F9F9F9')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#F9F9F9'), colors.white]),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph('Grade Distribution:', styles['HeaderStyle']))

    grade_data1 = [['O', 'A+', 'A', 'B+', 'B', 'C+', 'C', 'D+']]
    grade_data1.append([grade_counts[grade] for grade in grade_data1[0]])
    grade_table1 = Table(grade_data1, colWidths=[60] * 8)
    grade_table1.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E0E0E0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ]
        )
    )
    elements.append(grade_table1)
    elements.append(Spacer(1, 10))

    grade_data2 = [['D', 'F', 'I', 'S', 'X']]
    grade_data2.append([grade_counts[grade] for grade in grade_data2[0]])
    grade_table2 = Table(grade_data2, colWidths=[60] * 5)
    grade_table2.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E0E0E0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ]
        )
    )
    elements.append(grade_table2)
    elements.append(Spacer(1, 40))

    verified_style = styles['VerifiedStyle']
    elements.append(Paragraph('I have carefully checked and verified the submitted grade. The grade distribution and submitted grades are correct. [Please mention any exception below.]', verified_style))

    def draw_signatures(canvas, doc):
        canvas.saveState()
        width, height = letter
        canvas.drawString(inch, 0.75 * inch, '')
        canvas.drawString(inch, 0.5 * inch, 'Date')
        canvas.drawString(width - 4 * inch, 0.75 * inch, '')
        canvas.drawString(width - 4 * inch, 0.5 * inch, "Course Instructor's Signature")
        canvas.restoreState()

    doc.build(elements, onLaterPages=draw_signatures, onFirstPage=draw_signatures)
    buffer.seek(0)
    return buffer.getvalue(), f'{course_info.code}_grades.pdf'


def get_sample_pdf_styles():
    return {
        'HeaderStyle': ParagraphStyle(
            'HeaderStyle',
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=HexColor('#333333'),
            spaceAfter=20,
            alignment=1,
        ),
        'FieldLabelStyle': ParagraphStyle(
            'FieldLabelStyle',
            fontSize=12,
            textColor=colors.black,
            spaceAfter=5,
        ),
        'FieldValueStyle': ParagraphStyle(
            'FieldValueStyle',
            fontSize=12,
            textColor=HexColor('#666666'),
            spaceAfter=10,
        ),
        'VerifiedStyle': ParagraphStyle(
            'VerifiedStyle',
            fontSize=13,
            textColor=HexColor('#333333'),
            alignment=0,
            spaceAfter=20,
        ),
    }


def build_grade_result_workbook(branch, batch, semester):
    branch_info = Discipline.objects.filter(acronym=branch).first()
    if not branch_info:
        raise ValueError('Branch not found')

    curriculum_id = Batch.objects.filter(
        year=batch,
        discipline_id=branch_info.id
    ).values_list('curriculum_id', flat=True).first()
    if not curriculum_id:
        raise ValueError('Curriculum not found')

    semester_info = Semester.objects.filter(
        curriculum_id=curriculum_id,
        semester_no=semester
    ).first()
    if not semester_info:
        raise ValueError('Semester not found')

    course_slots = CourseSlot.objects.filter(semester_id=semester_info)
    course_ids_from_slots = course_slots.values_list('courses', flat=True)
    course_ids_from_grades = Student_grades.objects.filter(
        batch=batch,
        semester=semester
    ).values_list('course_id_id', flat=True)
    course_ids = set(course_ids_from_slots).union(set(course_ids_from_grades))
    courses = Courses.objects.filter(id__in=course_ids)
    courses_map = {course.id: course.credit for course in courses}
    students = Student.objects.filter(batch=batch, specialization=branch).order_by('id')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Student Grades'

    ws['A1'] = 'S. No'
    ws['B1'] = 'Roll No'
    for cell in ('A1', 'B1'):
        ws[cell].alignment = Alignment(horizontal='center', vertical='center')
        ws[cell].font = Font(bold=True)

    ws.column_dimensions[get_column_letter(1)].width = 12
    ws.column_dimensions[get_column_letter(2)].width = 18
    col_idx = 3

    for course in courses:
        ws.merge_cells(start_row=1, start_column=col_idx, end_row=1, end_column=col_idx + 1)
        ws.merge_cells(start_row=2, start_column=col_idx, end_row=2, end_column=col_idx + 1)
        ws.merge_cells(start_row=3, start_column=col_idx, end_row=3, end_column=col_idx + 1)

        ws.cell(row=1, column=col_idx).value = course.code
        ws.cell(row=1, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=1, column=col_idx).font = Font(bold=True)
        ws.cell(row=2, column=col_idx).value = course.name
        ws.cell(row=2, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=2, column=col_idx).font = Font(bold=True)
        ws.cell(row=3, column=col_idx).value = course.credit
        ws.cell(row=3, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=3, column=col_idx).font = Font(bold=True)
        ws.cell(row=4, column=col_idx).value = 'Grade'
        ws.cell(row=4, column=col_idx + 1).value = 'Remarks'
        ws.cell(row=4, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=4, column=col_idx + 1).alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[get_column_letter(col_idx)].width = 25
        ws.column_dimensions[get_column_letter(col_idx + 1)].width = 25
        col_idx += 2

    ws.cell(row=1, column=col_idx).value = 'SPI'
    ws.cell(row=1, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=1, column=col_idx).font = Font(bold=True)

    ws.cell(row=1, column=col_idx + 1).value = 'CPI'
    ws.cell(row=1, column=col_idx + 1).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=1, column=col_idx + 1).font = Font(bold=True)

    row_idx = 5
    for idx, student in enumerate(students, start=1):
        ws.cell(row=row_idx, column=1).value = idx
        ws.cell(row=row_idx, column=2).value = student.id_id
        ws.cell(row=row_idx, column=1).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=row_idx, column=2).alignment = Alignment(horizontal='center', vertical='center')

        student_grades = Student_grades.objects.filter(
            roll_no=student.id_id, course_id_id__in=course_ids, semester=semester
        )
        grades_map = {
            grade.course_id_id: (grade.grade, grade.remarks, courses_map.get(grade.course_id_id))
            for grade in student_grades
        }

        col_idx = 3
        gained_credit = 0
        total_credit = 0
        for course in courses:
            grade_value, remark, credits = grades_map.get(course.id, ('N/A', 'N/A', 0))
            ws.cell(row=row_idx, column=col_idx).value = grade_value
            ws.cell(row=row_idx, column=col_idx + 1).value = remark
            ws.cell(row=row_idx, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
            ws.cell(row=row_idx, column=col_idx + 1).alignment = Alignment(horizontal='center', vertical='center')
            if grade_value == 'O' or grade_value == 'A+':
                gained_credit += 1 * credits
                total_credit += credits
            elif grade_value == 'A':
                gained_credit += 0.9 * credits
                total_credit += credits
            elif grade_value == 'B+':
                gained_credit += 0.8 * credits
                total_credit += credits
            elif grade_value == 'B':
                gained_credit += 0.7 * credits
                total_credit += credits
            elif grade_value == 'C+':
                gained_credit += 0.6 * credits
                total_credit += credits
            elif grade_value == 'C':
                gained_credit += 0.5 * credits
                total_credit += credits
            elif grade_value == 'D+':
                gained_credit += 0.4 * credits
                total_credit += credits
            elif grade_value == 'D':
                gained_credit += 0.3 * credits
                total_credit += credits
            elif grade_value == 'F':
                gained_credit += 0.2 * credits
                total_credit += credits

            col_idx += 2

        ws.cell(row=row_idx, column=col_idx).value = 0 if total_credit == 0 else 10 * (gained_credit / total_credit)
        ws.cell(row=row_idx, column=col_idx + 1).value = 0
        ws.cell(row=row_idx, column=col_idx).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(row=row_idx, column=col_idx + 1).alignment = Alignment(horizontal='center', vertical='center')

        row_idx += 1

    return wb
