import datetime
import calendar
import pandas as pd
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import *
from .forms import EmployeeUserForm, StudentForm, TeacherForm, GroupForm, SessionForm, GradeForm, RoomForm, SubjectForm, GuestForm, EnrollmentForm
from datetime import timedelta
from django.utils import timezone

@login_required
def dashboard(request):
    today = timezone.localdate()
    
    # 1. حصص اليوم فقط
    today_sessions = Session.objects.filter(date=today).select_related('group', 'group__teacher')
    
    # 2. أرباح المركز اليوم (عدد الطلاب الذين دفعوا حق المركز مضروباً في قيمة حق المركز)
    today_center_paid = Attendance.objects.filter(
        session__date=today, 
        status='present', 
        is_center_paid=True
    ).select_related('session__group')
    
    center_cuts_today = sum(att.session.group.center_cut for att in today_center_paid)

    # 3. إجمالي تحصيلات اليوم (بدون أرباح المركز)
    today_attendances_paid = Attendance.objects.filter(session__date=today, is_paid=True, status='present')
    today_guests_paid = GuestAttendance.objects.filter(session__date=today, is_paid=True)
    
    raw_total_collections = sum(att.charged_price for att in today_attendances_paid) + sum(g.charged_price for g in today_guests_paid)
    total_collections_today = max(0, raw_total_collections - center_cuts_today)

    # 4. ديون الطلاب الحاضرين اليوم ولم يدفعوا
    today_unpaid_attendances = Attendance.objects.filter(session__date=today, status='present', is_paid=False)
    students_debt_today = sum(att.charged_price for att in today_unpaid_attendances)

    return render(request, 'center/dashboard.html', {
        'today': today,
        'today_sessions': today_sessions,
        'total_collections_today': total_collections_today,
        'center_cuts_today': center_cuts_today,
        'students_debt_today': students_debt_today,
    })

@login_required
def enrollment_edit_price(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    student_pk = enrollment.student.pk
    
    if request.method == 'POST':
        custom_price = request.POST.get('custom_price')
        if custom_price == '':
            enrollment.custom_price = None
        else:
            try:
                enrollment.custom_price = float(custom_price)
            except ValueError:
                pass
        enrollment.save()
        return redirect('center:student_detail', pk=student_pk)

    return render(request, 'center/enrollment_edit_price.html', {'enrollment': enrollment})

@login_required
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    student_pk = enrollment.student.pk
    if request.method == 'POST':
        # حذف سجلات الحضور غير المدفوعة أو المستقبلية المرتبطة بهذا التسجيل إذا أردت، أو حذف التسجيل مباشرة
        enrollment.delete()
        return redirect('center:student_detail', pk=student_pk)
    return render(request, 'center/confirm_delete.html', {'object': enrollment, 'title': 'إلغاء تسجيل الطالب من المجموعة'})

@login_required
def student_list(request):
    query = request.GET.get('q', '').strip()
    grade_id = request.GET.get('grade', '').strip()
    
    students_qs = Student.objects.all().order_by('-id')
    
    if query:
        students_qs = students_qs.filter(
            Q(code__iexact=query) | Q(name__icontains=query) | Q(phone__icontains=query) | Q(guardian_phone__icontains=query)
        )
    
    if grade_id:
        students_qs = students_qs.filter(grade_id=grade_id)

    paginator = Paginator(students_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    grades = Grade.objects.all()

    return render(request, 'center/student_list.html', {
        'page_obj': page_obj, 
        'query': query, 
        'grade_id': grade_id, 
        'grades': grades
    })

@login_required
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            return redirect('center:student_detail', pk=student.pk)
    else:
        form = StudentForm()
    return render(request, 'center/entity_form.html', {'form': form, 'title': 'إضافة طالب جديد'})

@login_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            return redirect('center:student_detail', pk=student.pk)
    else:
        form = StudentForm(instance=student)
    return render(request, 'center/student_edit.html', {'form': form, 'student': student, 'title': f'تعديل بيانات الطالب: {student.name}'})

@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        return redirect('center:student_list')
    return render(request, 'center/confirm_delete.html', {'object': student, 'title': 'حذف الطالب'})

@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    today = timezone.localdate()
    
    enrollments = student.enrollment_set.all()
    
    # استثناء المجموعات التي الطالب مسجل فيها بالفعل من القائمة المنسدلة
    enrolled_group_ids = enrollments.values_list('group_id', flat=True)
    available_groups = Group.objects.filter(grade=student.grade).exclude(id__in=enrolled_group_ids)
    
    attendances = Attendance.objects.filter(
        student=student, 
        session__date__lte=today
    ).order_by('-session__date')
    
    if request.method == 'POST' and 'add_to_group' in request.POST:
        enrollment_form = EnrollmentForm(request.POST, student_grade=student.grade)
        if enrollment_form.is_valid():
            enr = enrollment_form.save(commit=False)
            enr.student = student
            enr.save()
            return redirect('center:student_detail', pk=student.pk)
    else:
        enrollment_form = EnrollmentForm(student_grade=student.grade)
        # تخصيص الـ queryset ليعرض المجموعات المتاحة فقط التي لم يجل بها
        enrollment_form.fields['group'].queryset = available_groups

    return render(request, 'center/student_detail.html', {
        'student': student,
        'enrollments': enrollments,
        'attendances': attendances,
        'enrollment_form': enrollment_form,
        'available_groups': available_groups, # تمرير المجموعات المتاحة للقالب
    })

@login_required
def group_list(request):
    query = request.GET.get('q', '').strip()
    grade_id = request.GET.get('grade', '').strip()
    sort_by = request.GET.get('sort', '-id').strip()

    groups_qs = Group.objects.all()

    # التصفية والبحث
    if query:
        groups_qs = groups_qs.filter(
            Q(name__icontains=query) | 
            Q(subject__name__icontains=query) | 
            Q(teacher__name__icontains=query)
        )
    
    if grade_id:
        groups_qs = groups_qs.filter(grade_id=grade_id)

    # الترتيب والفرز التفاعلي
    valid_sorts = {
        'name': 'name', '-name': '-name',
        'subject': 'subject__name', '-subject': '-subject__name',
        'teacher': 'teacher__name', '-teacher': '-teacher__name',
        'grade': 'grade__name', '-grade': '-grade__name',
        'day': 'day_of_week', '-day': '-day_of_week',
        'time': 'time', '-time': '-time',
    }
    order_field = valid_sorts.get(sort_by, '-id')
    groups_qs = groups_qs.order_by(order_field)

    grades = Grade.objects.all()
    
    paginator = Paginator(groups_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'center/group_list.html', {
        'page_obj': page_obj,
        'query': query,
        'grade_id': grade_id,
        'grades': grades,
        'sort_by': sort_by,
    })

@login_required
def group_add(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            return redirect('center:group_detail', pk=group.pk)
    else:
        form = GroupForm()
    return render(request, 'center/entity_form.html', {'form': form, 'title': 'إضافة مجموعة جديدة'})

@login_required
def group_edit(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('center:group_detail', pk=group.pk)
    else:
        form = GroupForm(instance=group)
    return render(request, 'center/entity_form.html', {'form': form, 'title': f'تعديل المجموعة: {group}'})

@login_required
def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk)
    today = timezone.localdate()

    # 1. جلب تسجيلات الطلاب مع الترقيم
    enrollments_list = group.enrollment_set.select_related('student').all().order_by('student__name')
    students_paginator = Paginator(enrollments_list, 10)
    students_page = students_paginator.get_page(request.GET.get('students_page'))

    # 2. جلب حصص المجموعة مع الترقيم
    sessions_list = group.session_set.all().order_by('-date')
    sessions_paginator = Paginator(sessions_list, 10)
    sessions_page = sessions_paginator.get_page(request.GET.get('sessions_page'))

    return render(request, 'center/group_detail.html', {
        'group': group,
        'students_page': students_page,
        'sessions_page': sessions_page,
    })

@login_required
def teacher_list(request):
    query = request.GET.get('q', '').strip()
    teachers = Teacher.objects.all()
    
    if query:
        teachers = teachers.filter(
            Q(name__icontains=query) | Q(phone__icontains=query)
        )
        
    return render(request, 'center/teacher_list.html', {
        'teachers': teachers,
        'query': query,
    })

@login_required
def teacher_detail(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    today = timezone.localdate()
    
    # معالجة عملية صرف المستحقات للمعلم
    if request.method == 'POST':
        amount = request.POST.get('amount')
        note = request.POST.get('note', '')
        date = request.POST.get('date', timezone.now())
        
        if amount:
            TeacherPayout.objects.create(
                teacher=teacher,
                amount=amount,
                date=date,
                note=note
            )
            return redirect('center:teacher_detail', pk=teacher.pk)

    payouts = teacher.payouts.all().order_by('-date')
    
    # جلب الحصص السابقة والحالية فقط (date <= today) وإخفاء الحصص المستقبلية
    groups = teacher.group_set.all()
    sessions = Session.objects.filter(group__in=groups, date__lte=today).order_by('-date')

    # تجهيز بيانات الحصص مع حساب حصيلة المبلغ لكل حصة بدقة
    sessions_data = []
    for s in sessions:
        # حساب مجموع أسعار الحضور المدفوعة للطلاب في هذه الحصة
        attendances_sum = sum(a.charged_price for a in s.attendance_set.filter(is_paid=True))
        # حساب مجموع رسوم الضيوف المدفوعة في هذه الحصة
        guests_sum = sum(g.charged_price for g in s.guestattendance_set.filter(is_paid=True))
        
        total_session_revenue = attendances_sum + guests_sum
        
        sessions_data.append({
            'session': s,
            'total_revenue': total_session_revenue
        })

    return render(request, 'center/teacher_detail.html', {
        'teacher': teacher,
        'payouts': payouts,
        'sessions_data': sessions_data,
        'balance_due': teacher.balance_due, # المبلغ المستحق على المركز للمعلم
    })

@login_required
def teacher_add(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('center:teacher_list')
    else:
        form = TeacherForm()
    return render(request, 'center/entity_form.html', {'form': form, 'title': 'إضافة معلم جديد'})

@login_required
def teacher_edit(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            return redirect('center:teacher_list')
    else:
        form = TeacherForm(instance=teacher)
    return render(request, 'center/entity_form.html', {'form': form, 'title': f'تعديل بيانات المعلم: {teacher.name}'})

# --- Sessions Management Views with Independent Date Filter (Default to Today) ---
@login_required
def session_list(request):
    today = timezone.localdate()
    query = request.GET.get('q', '').strip()
    
    month_param = request.GET.get('month', '').strip()
    year_param = request.GET.get('year', '').strip()

    if '-' in month_param:
        try:
            parts = month_param.split('-')
            selected_year = int(parts[0])
            selected_month = int(parts[1])
        except ValueError:
            selected_year = today.year
            selected_month = today.month
    else:
        try:
            selected_year = int(year_param) if year_param else today.year
        except ValueError:
            selected_year = today.year
            
        try:
            selected_month = int(month_param) if month_param else today.month
        except ValueError:
            selected_month = today.month

    sort_by = request.GET.get('sort', 'date').strip()

    sessions_qs = Session.objects.filter(date__year=selected_year, date__month=selected_month)

    if query:
        sessions_qs = sessions_qs.filter(
            Q(group__name__icontains=query) | 
            Q(group__subject__name__icontains=query) | 
            Q(group__teacher__name__icontains=query)
        )

    valid_sorts = {
        'date': 'date', '-date': '-date',
        'group': 'group__name', '-group': '-group__name',
        'teacher': 'group__teacher__name', '-teacher': '-group__teacher__name',
        'status': 'status', '-status': '-status'
    }
    order_field = valid_sorts.get(sort_by, 'date')
    sessions_qs = sessions_qs.order_by(order_field)

    paginator = Paginator(sessions_qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    # نطاق أوسع للسنوات (مثلاً من قبل سنتين إلى 5 سنوات قادمة)
    years_list = range(today.year - 2, today.year + 6)
    
    months_list = [
        (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'), (4, 'أبريل'),
        (5, 'مايو'), (6, 'يونيو'), (7, 'يوليو'), (8, 'أغسطس'),
        (9, 'سبتمبر'), (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر')
    ]

    is_past_period = (selected_year < today.year) or (selected_year == today.year and selected_month < today.month)

    return render(request, 'center/session_list.html', {
        'page_obj': page_obj,
        'query': query,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'years_list': years_list,
        'months_list': months_list,
        'sort_by': sort_by,
        'is_past_period': is_past_period,
    })

@login_required
def change_session_status(request, pk, new_status):
    session = get_object_or_404(Session, pk=pk)
    if new_status in ['completed', 'canceled', 'scheduled']:
        session.status = new_status
        session.save()
    return redirect(request.META.get('HTTP_REFERER', 'center:dashboard'))

@login_required
def generate_monthly_lessons_page(request):
    """صفحة لاختيار المجموعات وتوليد حصص الشهر لها مع منع التكرار"""
    today = timezone.localdate()
    
    month_param = request.GET.get('month', '').strip()
    year_param = request.GET.get('year', '').strip()

    if '-' in month_param:
        try:
            parts = month_param.split('-')
            selected_year = int(parts[0])
            selected_month = int(parts[1])
        except ValueError:
            selected_year = today.year
            selected_month = today.month
    else:
        try:
            selected_year = int(year_param) if year_param else today.year
        except ValueError:
            selected_year = today.year
            
        try:
            selected_month = int(month_param) if month_param else today.month
        except ValueError:
            selected_month = today.month

    # منع التوليد للأشهر السابقة
    if (selected_year < today.year) or (selected_year == today.year and selected_month < today.month):
        return redirect('center:session_list')

    all_groups = Group.objects.all()
    
    # فحص المجموعات التي تم إنشاء حصص لها مسبقاً في هذا الشهر والسنة
    groups_data = []
    for group in all_groups:
        already_generated = Session.objects.filter(
            group=group, 
            date__year=selected_year, 
            date__month=selected_month
        ).exists()
        
        groups_data.append({
            'group': group,
            'already_generated': already_generated
        })

    if request.method == 'POST':
        selected_group_ids = request.POST.getlist('group_ids')
        target_groups = Group.objects.filter(id__in=selected_group_ids)

        for group in target_groups:
            # التأكد مرة أخرى برمجياً من عدم وجود حصص مسبقة لنفس الشهر قبل التوليد
            has_sessions = Session.objects.filter(
                group=group, 
                date__year=selected_year, 
                date__month=selected_month
            ).exists()
            
            if not has_sessions:
                group.generate_current_month_sessions(year=selected_year, month=selected_month)

        return redirect(f'/sessions/?year={selected_year}&month={selected_month}')

    return render(request, 'center/generate_monthly_lessons.html', {
        'groups_data': groups_data,
        'selected_year': selected_year,
        'selected_month': selected_month,
    })

@login_required
def session_detail(request, pk):
    session = get_object_or_404(Session, pk=pk)
    group = session.group
    
    # 1. جلب تسجيلات الطلاب في المجموعة مع الأسعار المخصصة
    enrollments = group.enrollment_set.select_related('student').all()
    
    # إنشاء قاموس يربط معرف الطالب بسعره الفعلي المخصص (custom_price أو session_price)
    student_custom_prices = {enr.student.id: enr.get_price() for enr in enrollments}

    # 2. التأكد من إنشاء سجلات الحضور وتحديث سعرها المطلوب ليطابق سعر الطالب المخصص فوراً
    for enr in enrollments:
        att, created = Attendance.objects.get_or_create(
            session=session,
            student=enr.student,
            defaults={
                'status': 'absent', 
                'charged_price': enr.get_price(), 
                'is_paid': False
            }
        )
        # تحديث السعر مباشرة إذا كان مختلفاً عن السعر المخصص للطالب
        if att.charged_price != enr.get_price():
            att.charged_price = enr.get_price()
            att.save()

    # 3. جلب سجلات الحضور الخاصة بهذه الحصة
    attendances_qs = session.attendance_set.select_related('student').all()

    # شريط البحث (بالاسم أو الكود)
    query = request.GET.get('q', '').strip()
    if query:
        attendances_qs = attendances_qs.filter(
            Q(student__name__icontains=query) | Q(student__code__icontains=query)
        )

    # فلتر التصفية (حاضر / غائب)
    attendance_filter = request.GET.get('filter', '').strip()
    if attendance_filter == 'present':
        attendances_qs = attendances_qs.filter(status='present')
    elif attendance_filter == 'absent':
        attendances_qs = attendances_qs.filter(status='absent')

    # معالجة حفظ الحضور والدفع
    if request.method == 'POST':
        for att in attendances_qs:
            is_present_checked = f'present_{att.student.id}' in request.POST
            is_paid_checked = f'paid_{att.student.id}' in request.POST
            is_center_paid_checked = f'center_paid_{att.student.id}' in request.POST # استقبال حق المركز
            
            student_price = student_custom_prices.get(att.student.id, group.session_price)

            att.status = 'present' if is_present_checked else 'absent'
            att.charged_price = student_price
            att.is_paid = is_paid_checked if att.status == 'present' else False
            att.is_center_paid = is_center_paid_checked if att.status == 'present' else False
            att.save()
            
        return redirect('center:session_detail', pk=session.pk)

    guests = session.guestattendance_set.all()

    return render(request, 'center/session_detail.html', {
        'session': session,
        'group': group,
        'attendances': attendances_qs,
        'guests': guests,
        'query': query,
        'attendance_filter': attendance_filter,
    })

@login_required
def guest_add(request, session_pk):
    session_obj = get_object_or_404(Session, pk=session_pk)
    if request.method == 'POST':
        form = GuestForm(request.POST)
        if form.is_valid():
            guest = form.save(commit=False)
            guest.session = session_obj
            guest.save()
            return redirect('center:session_detail', pk=session_obj.pk)
    else:
        form = GuestForm(initial={'charged_price': session_obj.group.session_price})
    return render(request, 'center/entity_form.html', {'form': form, 'title': f'إضافة ضيف للحصة: {session_obj}'})

@login_required
def session_add(request):
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            enrolled_students = Enrollment.objects.filter(group=session.group)
            for enr in enrolled_students:
                Attendance.objects.get_or_create(session=session, student=enr.student, defaults={'status': 'present'})
            return redirect('center:session_list')
    else:
        form = SessionForm()
    return render(request, 'center/entity_form.html', {'form': form, 'title': 'إضافة / جدولة حصة دراسية جديدة'})

@login_required
def session_edit(request, pk):
    session_obj = get_object_or_404(Session, pk=pk)
    if request.method == 'POST':
        form = SessionForm(request.POST, instance=session_obj)
        if form.is_valid():
            form.save()
            return redirect('center:session_list')
    else:
        form = SessionForm(instance=session_obj)
    return render(request, 'center/entity_form.html', {'form': form, 'title': f'تعديل الحصة: {session_obj}'})

@login_required
def session_delete(request, pk):
    session_obj = get_object_or_404(Session, pk=pk)
    if request.method == 'POST':
        session_obj.delete()
        return redirect('center:session_list')
    return render(request, 'center/confirm_delete.html', {'object': session_obj, 'title': 'حذف الحصة الدراسية'})

@login_required
def setup_hub(request):
    grades = Grade.objects.all()
    rooms = Room.objects.all()
    subjects = Subject.objects.all()
    return render(request, 'center/setup_hub.html', {'grades': grades, 'rooms': rooms, 'subjects': subjects})

@login_required
def grade_add(request):
    form = GradeForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('center:setup_hub')
    return render(request, 'center/entity_form.html', {'form': form, 'title': 'إضافة صف دراسي'})

@login_required
def room_add(request):
    form = RoomForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('center:setup_hub')
    return render(request, 'center/entity_form.html', {'form': form, 'title': 'إضافة قاعة دراسية'})

@login_required
def subject_add(request):
    form = SubjectForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('center:setup_hub')
    return render(request, 'center/entity_form.html', {'form': form, 'title': 'إضافة مادة دراسية'})

@login_required
def room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        room.delete()
        return redirect('center:setup_hub')
    return render(request, 'center/confirm_delete.html', {'object': room, 'title': 'حذف القاعة'})

@login_required
def grade_delete(request, pk):
    grade = get_object_or_404(Grade, pk=pk)
    if request.method == 'POST':
        grade.delete()
        return redirect('center:setup_hub')
    return render(request, 'center/confirm_delete.html', {'object': grade, 'title': 'حذف الصف الدراسي'})

@login_required
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        subject.delete()
        return redirect('center:setup_hub')
    return render(request, 'center/confirm_delete.html', {'object': subject, 'title': 'حذف المادة الدراسية'})

@login_required
def center_account(request):
    today = timezone.localdate()
    
    # 1. الحسابات العامة (الإجمالية الكلية)
    all_paid_attendances = Attendance.objects.filter(is_paid=True, status='present')
    all_paid_guests = GuestAttendance.objects.filter(is_paid=True)
    
    total_collections_all = sum(a.charged_price for a in all_paid_attendances) + sum(g.charged_price for g in all_paid_guests)
    
    all_center_paid = Attendance.objects.filter(status='present', is_center_paid=True).select_related('session__group')
    total_center_cuts_all = sum(att.session.group.center_cut for att in all_center_paid)
    
    total_payouts_all = sum(p.amount for p in TeacherPayout.objects.all())

    # 2. تقرير مخصص من تاريخ إلى تاريخ (Custom Date Range)
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    custom_collections = 0
    custom_center_cuts = 0
    custom_payouts = 0
    has_custom_filter = False

    if start_date_str and end_date_str:
        has_custom_filter = True
        custom_attendances = Attendance.objects.filter(session__date__gte=start_date_str, session__date__lte=end_date_str, is_paid=True, status='present')
        custom_guests = GuestAttendance.objects.filter(session__date__gte=start_date_str, session__date__lte=end_date_str, is_paid=True)
        custom_center_paid = Attendance.objects.filter(session__date__gte=start_date_str, session__date__lte=end_date_str, status='present', is_center_paid=True).select_related('session__group')
        
        custom_collections = sum(a.charged_price for a in custom_attendances) + sum(g.charged_price for g in custom_guests)
        custom_center_cuts = sum(att.session.group.center_cut for att in custom_center_paid)
        custom_payouts = sum(p.amount for p in TeacherPayout.objects.filter(date__date__gte=start_date_str, date__date__lte=end_date_str))

    # 3. التقرير الشهري (اختر الشهر والسنة من القائمة)
    selected_month = request.GET.get('month', str(today.month))
    selected_year = request.GET.get('year', str(today.year))
    
    monthly_collections = 0
    monthly_center_cuts = 0
    monthly_payouts = 0

    if selected_month and selected_year:
        m_attendances = Attendance.objects.filter(session__date__year=int(selected_year), session__date__month=int(selected_month), is_paid=True, status='present')
        m_guests = GuestAttendance.objects.filter(session__date__year=int(selected_year), session__date__month=int(selected_month), is_paid=True)
        m_center_paid = Attendance.objects.filter(session__date__year=int(selected_year), session__date__month=int(selected_month), status='present', is_center_paid=True).select_related('session__group')
        
        monthly_collections = sum(a.charged_price for a in m_attendances) + sum(g.charged_price for g in m_guests)
        monthly_center_cuts = sum(att.session.group.center_cut for att in m_center_paid)
        monthly_payouts = sum(p.amount for p in TeacherPayout.objects.filter(date__date__year=int(selected_year), date__date__month=int(selected_month)))

    return render(request, 'center/center_account.html', {
        'total_collections_all': total_collections_all,
        'total_center_cuts_all': total_center_cuts_all,
        'total_payouts_all': total_payouts_all,
        
        'has_custom_filter': has_custom_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'custom_collections': custom_collections,
        'custom_center_cuts': custom_center_cuts,
        'custom_payouts': custom_payouts,
        
        'selected_month': selected_month,
        'selected_year': selected_year,
        'monthly_collections': monthly_collections,
        'monthly_center_cuts': monthly_center_cuts,
        'monthly_payouts': monthly_payouts,
    })

    return render(request, 'center/center_account.html', {
        'total_collections_all': total_collections_all,
        'total_center_cuts_all': total_center_cuts_all,
        'total_payouts_all': total_payouts_all,
        'weekly_collections': weekly_collections,
        'weekly_center_cuts': weekly_center_cuts,
        'weekly_payouts': weekly_payouts,
        'start_of_week': start_of_week,
        'today': today,
        'months_data': months_data,
        'current_year': current_year,
    })

@login_required
def import_excel_students(request):
    message = None
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            df = pd.read_excel(excel_file)
            imported_count = 0
            default_grade = Grade.objects.first()
            for _, row in df.iterrows():
                name = str(row.get('name', 'الطالب')).strip()
                phone = str(row.get('phone', ''))
                if name and name != 'nan':
                    Student.objects.get_or_create(name=name, defaults={'phone': phone, 'grade': default_grade})
                    imported_count += 1
            message = f"تم استيراد {imported_count} طالب بنجاح من ملف Excel!"
        except Exception as e:
            message = f"حدث خطأ أثناء قراءة الملف: {e}"
    return render(request, 'center/import_excel.html', {'message': message})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def employee_management(request):
    employees = User.objects.all()
    message = None
    if request.method == 'POST':
        form = EmployeeUserForm(request.POST)
        if form.is_valid():
            form.save()
            message = "تم إضافة حساب الموظف بنجاح!"
            form = EmployeeUserForm()
    else:
        form = EmployeeUserForm()
    return render(request, 'center/employees.html', {'employees': employees, 'form': form, 'message': message})



import os
import shutil
from django.http import HttpResponse, Http404
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser)
def backup_restore_view(request):
    db_path = settings.DATABASES['default']['NAME']
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, 'db_backup.sqlite3')

    # 1. إذا طلب المدير تحميل النسخة الاحتياطية
    if 'download_backup' in request.GET:
        if not os.path.exists(backup_file):
            shutil.copy2(db_path, backup_file)
        if os.path.exists(backup_file):
            with open(backup_file, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="application/x-sqlite3")
                response['Content-Disposition'] = 'inline; filename=' + os.path.basename(backup_file)
                return response
        raise Http404("ملف النسخة الاحتياطية غير موجود.")

    # 2. إذا قام المدير برفع ملف لاستعادته
    if request.method == 'POST' and 'restore_file' in request.FILES:
        uploaded_file = request.FILES['restore_file']
        temp_file_path = os.path.join(backup_dir, uploaded_file.name)
        
        with open(temp_file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
                
        # استبدال قاعدة البيانات الحالية بالملف المرفوع
        shutil.copy2(temp_file_path, db_path)
        return redirect('center:backup_restore')

    return render(request, 'center/backup_restore.html')


from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_superuser)
def employee_list_view(request):
    # كود عرض الموظفين...
    return render(request, 'center/employee_list.html', {})

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

@user_passes_test(lambda u: u.is_superuser)
def employee_list_view(request):
    employees = User.objects.all().order_by('-id')
    
    # 1. إضافة موظف جديد
    if request.method == 'POST' and 'add_employee' in request.POST:
        username = request.POST.get('username')
        full_name = request.POST.get('full_name')
        password = request.POST.get('password')
        is_staff = 'is_staff' in request.POST
        
        if username and password:
            user = User.objects.create_user(username=username, password=password, first_name=full_name)
            user.is_staff = is_staff
            user.save()
        return redirect('center:employee_list')

    return render(request, 'center/employee_list.html', {
        'employees': employees,
    })

@user_passes_test(lambda u: u.is_superuser)
def employee_edit_view(request, pk):
    employee = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        new_password = request.POST.get('password')
        is_staff = 'is_staff' in request.POST
        is_superuser = 'is_superuser' in request.POST
        
        employee.first_name = full_name
        employee.is_staff = is_staff
        employee.is_superuser = is_superuser
        
        if new_password: # تحديث كلمة المرور فقط إذا تم إدخال واحدة جديدة
            employee.set_password(new_password)
            
        employee.save()
        return redirect('center:employee_list')
        
    return render(request, 'center/employee_edit.html', {'employee': employee})

@user_passes_test(lambda u: u.is_superuser)
def employee_delete_view(request, pk):
    employee = get_object_or_404(User, pk=pk)
    if employee != request.user: # منع المدير من حذف نفسه بالخطأ
        employee.delete()
    return redirect('center:employee_list')