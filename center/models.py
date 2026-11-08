import calendar
import datetime
from django.db import models
from django.utils import timezone

class Grade(models.Model):
    name = models.CharField(max_length=100, verbose_name="الصف الدراسي")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "صف دراسي"
        verbose_name_plural = "الصفوف الدراسية"


class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم المادة")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "مادة دراسية"
        verbose_name_plural = "المواد الدراسية"


class Teacher(models.Model):
    name = models.CharField(max_length=150, verbose_name="اسم المعلم")
    phone = models.CharField(max_length=20, verbose_name="رقم الهاتف")
    subjects = models.ManyToManyField(Subject, verbose_name="المواد التي تدّرس")

    def __str__(self):
        return self.name

    @property
    def balance_due(self):
        today = timezone.localdate()
        # جلب الحصص السابقة والحالية فقط للمجموعة الخاصة بهذا المعلم
        groups = self.group_set.all()
        sessions = Session.objects.filter(group__in=groups, date__lte=today)
        
        total_collected = 0
        for s in sessions:
            # مجموع الحصص المدفوعة من الطلاب الحاضرين
            att_sum = sum(a.charged_price for a in s.attendance_set.filter(is_paid=True))
            # مجموع رسوم الضيوف المدفوعة
            guest_sum = sum(g.charged_price for g in s.guestattendance_set.filter(is_paid=True))
            total_collected += (att_sum + guest_sum)
            
        # ناقص إجمالي المبالغ التي تم صرفها للمعلم مسبقاً
        total_payouts = sum(p.amount for p in self.payouts.all())
        
        return total_collected - total_payouts

    class Meta:
        verbose_name = "معلم"
        verbose_name_plural = "المعلمون"


class Room(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم القاعة / الغرفة")
    capacity = models.PositiveIntegerField(default=30, verbose_name="السعة القصوى")

    def __str__(self):
        return f"{self.name} (السعة: {self.capacity})"

    class Meta:
        verbose_name = "قاعة"
        verbose_name_plural = "القاعات"


class Group(models.Model):
    name = models.CharField(max_length=150, verbose_name="اسم المجموعة")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="المادة")
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, verbose_name="الصف")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name="المعلم")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="القاعة المفضلة")
    day_of_week = models.IntegerField(default=5, choices=[
        (5, 'السبت'),
        (6, 'الأحد'),
        (0, 'الإثنين'),
        (1, 'الثلاثاء'),
        (2, 'الأربعاء'),
        (3, 'الخميس'),
        (4, 'الجمعة'),
    ], verbose_name="يوم الحصة الأسبوعي")
    time = models.TimeField(verbose_name="وقت الحصة")
    session_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="سعر الحصة الافتراضي للطالب")
    center_cut = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="نصيب المركز لكل مقعد")
    max_students = models.PositiveIntegerField(default=25, verbose_name="الحد الأقصى للطلاب")

    def __str__(self):
        return f"{self.name} - {self.subject.name} ({self.teacher.name})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.generate_current_month_sessions()

    def generate_current_month_sessions(self, year=None, month=None):
        today = timezone.localdate()
        year = year or today.year
        month = month or today.month
        num_days = calendar.monthrange(year, month)[1]

        for d in range(1, num_days + 1):
            date_obj = datetime.date(year, month, d)
            if date_obj.weekday() == self.day_of_week:
                Session.objects.get_or_create(
                    group=self,
                    date=date_obj,
                    defaults={'status': 'scheduled', 'notes': f'حصة شهر {month}/{year}'}
                )

    class Meta:
        verbose_name = "مجموعة"
        verbose_name_plural = "المجموعات"


class Student(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True, verbose_name="كود الطالب (أرقام فقط)")
    name = models.CharField(max_length=150, verbose_name="اسم الطالب")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم هاتف الطالب")
    guardian_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم ولي الأمر")
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, verbose_name="الصف الدراسي")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسجيل")

    def save(self, *args, **kwargs):
        if not self.code:
            last_student = Student.objects.all().order_by('-id').first()
            if last_student and last_student.code.isdigit():
                next_id = int(last_student.code) + 1
            else:
                next_id = 1001
            self.code = str(next_id)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_debt(self):
        unpaid_attendances = Attendance.objects.filter(student=self, status__in=['present', 'late'], is_paid=False)
        return sum(a.charged_price for a in unpaid_attendances)

    class Meta:
        verbose_name = "طالب"
        verbose_name_plural = "الطلاب"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="المجموعة")
    custom_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="سعر خاص (تخفيض)")
    joined_at = models.DateField(default=timezone.now, verbose_name="تاريخ الانضمام")

    def get_price(self):
        if self.custom_price is not None:
            return self.custom_price
        return self.group.session_price

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            future_sessions = Session.objects.filter(group=self.group, date__gte=self.joined_at)
            for s in future_sessions:
                Attendance.objects.get_or_create(session=s, student=self.student, defaults={'status': 'present'})

    def __str__(self):
        return f"{self.student.name} في {self.group}"

    class Meta:
        verbose_name = "تسجيل طالب بمجموعة"
        verbose_name_plural = "التسجيلات"
        unique_together = ('student', 'group')


class Session(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'مجدولة'),
        ('completed', 'تمت بنجاح'),
        ('canceled', 'ملغاة'),
        ('rescheduled', 'تم تغيير موعدها أو وقتها'),
    ]
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="المجموعة")
    date = models.DateField(default=timezone.now, verbose_name="تاريخ الحصة")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="حالة الحصة")
    rescheduled_date = models.DateField(blank=True, null=True, verbose_name="التاريخ الجديد (في حال التغيير)")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات الحصة")

    def __str__(self):
        return f"حصة {self.group.name} - {self.date} ({self.get_status_display()})"

    class Meta:
        verbose_name = "حصة دراسية"
        verbose_name_plural = "الحصص الدراسية"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غائب'),
        ('late', 'متأخر'),
    ]
    session = models.ForeignKey(Session, on_delete=models.CASCADE, verbose_name="الحصة")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present', verbose_name="الحالة")
    charged_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="السعر المطلوب")
    is_paid = models.BooleanField(default=False, verbose_name="تم دفع الحصة؟") # تم إعادة التسمية
    is_center_paid = models.BooleanField(default=False, verbose_name="تم دفع حق المركز؟") # حقل جديد لحق المركز

    def save(self, *args, **kwargs):
        if not self.pk and self.charged_price == 0 and self.status in ['present', 'late']:
            try:
                enrollment = Enrollment.objects.get(student=self.student, group=self.session.group)
                self.charged_price = enrollment.get_price()
            except Enrollment.DoesNotExist:
                self.charged_price = self.session.group.session_price
        elif self.status == 'absent':
            self.charged_price = 0
            self.is_paid = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.name} - {self.session} ({self.get_status_display()})"

    class Meta:
        verbose_name = "سجل الحضور"
        verbose_name_plural = "سجلات الحضور"
        unique_together = ('session', 'student')


class GuestAttendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, verbose_name="الحصة")
    guest_name = models.CharField(max_length=150, verbose_name="اسم الضيف / الزائر")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم الهاتف")
    charged_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="رسوم الحضور")
    is_paid = models.BooleanField(default=False, verbose_name="تم الدفع؟")

    def __str__(self):
        return f"ضيف: {self.guest_name} في {self.session}"

    class Meta:
        verbose_name = "حضور ضيف"
        verbose_name_plural = "حضور الضيوف"


class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'نقدي (Cash)'),
        ('vodafone_cash', 'فودافون كاش'),
        ('instapay', 'انستاباي (InstaPay)'),
        ('ee_cash', 'إي آند كاش (e& cash)'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    attendance_records = models.ManyToManyField(Attendance, verbose_name="الحصص المغطاة بالدفع")
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name="المبلغ المدفوع")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash', verbose_name="طريقة الدفع")
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="رقم الإيصال / العملية")
    date = models.DateTimeField(default=timezone.now, verbose_name="تاريخ الدفع")
    center_cut = models.DecimalField(max_digits=9, decimal_places=2, verbose_name="نصيب المركز الإجمالي")
    teacher_share = models.DecimalField(max_digits=9, decimal_places=2, verbose_name="نصيب المعلم الإجمالي")

    def save(self, *args, **kwargs):
        if not self.pk or not self.center_cut:
            total_center = 0
            total_teacher = 0
            remaining_amount = float(self.amount)
            for att in self.attendance_records.all():
                group_cut = float(att.session.group.center_cut)
                session_price = float(att.charged_price)
                teacher_part = max(0.0, session_price - group_cut)

                c_cut = min(group_cut, remaining_amount)
                remaining_amount -= c_cut
                total_center += c_cut

                t_share = min(teacher_part, remaining_amount)
                remaining_amount -= t_share
                total_teacher += t_share

            self.center_cut = total_center
            self.teacher_share = total_teacher
        super().save(*args, **kwargs)

    def __str__(self):
        return f"دفع {self.student.name} - {self.amount} ج.م ({self.get_method_display()})"

    class Meta:
        verbose_name = "عملية دفع"
        verbose_name_plural = "مدفوعات الطلاب"


class TeacherPayout(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='payouts', verbose_name="المعلم")
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name="المبلغ المدفوع للمعلم")
    date = models.DateTimeField(default=timezone.now, verbose_name="تاريخ الصرف")
    note = models.TextField(blank=True, null=True, verbose_name="ملاحظات / إيصال الصرف")

    def __str__(self):
        return f"صرف {self.amount} ج.م لـ {self.teacher.name}"

    class Meta:
        verbose_name = "صرف مستحقات معلم"
        verbose_name_plural = "صرف مستحقات المعلمين"
