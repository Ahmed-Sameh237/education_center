import os
import django
import datetime
import calendar

# تهيئة بيئة Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from center.models import Grade, Subject, Teacher, Room, Group, Student, Enrollment, Session, Attendance, GuestAttendance, Payment, TeacherPayout
from django.utils import timezone

def run():
    print("🚀 بدء إنشاء البيانات التجريبية...")

    # 1. إنشاء الصفوف الدراسية (Grades)
    grade1, _ = Grade.objects.get_or_create(name="الصف الأول الثانوي")
    grade2, _ = Grade.objects.get_or_create(name="الصف الثاني الثانوي")
    grade3, _ = Grade.objects.get_or_create(name="الصف الثالث الثانوي")
    print("✅ تم إنشاء الصفوف الدراسية.")

    # 2. إنشاء المواد الدراسية (Subjects)
    math, _ = Subject.objects.get_or_create(name="الرياضيات")
    physics, _ = Subject.objects.get_or_create(name="الفيزياء")
    arabic, _ = Subject.objects.get_or_create(name="اللغة العربية")
    english, _ = Subject.objects.get_or_create(name="اللغة الإنجليزية")
    print("✅ تم إنشاء المواد الدراسية.")

    # 3. إنشاء القاعات (Rooms)
    room_a, _ = Room.objects.get_or_create(name="قاعة أكتيف (1)", capacity=35)
    room_b, _ = Room.objects.get_or_create(name="قاعة التفوق (2)", capacity=25)
    print("✅ تم إنشاء القاعات.")

    # 4. إنشاء المعلمين (Teachers)
    t_ahmed, _ = Teacher.objects.get_or_create(name="أ/ أحمد كمال", phone="01011112222")
    t_ahmed.subjects.add(math, physics)

    t_hassan, _ = Teacher.objects.get_or_create(name="أ/ حسن محمود", phone="01133334444")
    t_hassan.subjects.add(arabic)

    t_sara, _ = Teacher.objects.get_or_create(name="د/ سارة علي", phone="01255556666")
    t_sara.subjects.add(english)
    print("✅ تم إنشاء المعلمين.")

    # 5. إنشاء المجموعات (Groups) - عند إنشائها سيتم تلقائياً إنشاء حصص الشهر الحالي
    # (ملاحظة: day_of_week: 5 = السبت، 6 = الأحد، 0 = الإثنين، 1 = الثلاثاء...)
    g_math1, _ = Group.objects.get_or_create(
        name="مجموعة الرياضيات - أولى ثانوي",
        subject=math,
        grade=grade1,
        teacher=t_ahmed,
        room=room_a,
        day_of_week=5, # السبت
        time=datetime.time(14, 0),
        session_price=60.00,
        center_cut=15.00,
        max_students=30
    )

    g_phys2, _ = Group.objects.get_or_create(
        name="مجموعة الفيزياء - ثانية ثانوي",
        subject=physics,
        grade=grade2,
        teacher=t_ahmed,
        room=room_b,
        day_of_week=0, # الإثنين
        time=datetime.time(16, 0),
        session_price=70.00,
        center_cut=20.00,
        max_students=25
    )

    g_arab1, _ = Group.objects.get_or_create(
        name="مجموعة العربي - أولى ثانوي",
        subject=arabic,
        grade=grade1,
        teacher=t_hassan,
        room=room_a,
        day_of_week=1, # الثلاثاء
        time=datetime.time(15, 30),
        session_price=50.00,
        center_cut=10.00,
        max_students=35
    )
    print("✅ تم إنشاء المجموعات الحالية وحصصها الشهرية تلقائياً.")

    # 6. إنشاء الطلاب (Students)
    students_data = [
        {"name": "محمد السيد علي", "phone": "01099887766", "guardian": "01122334455", "grade": grade1},
        {"name": "عمر خالد يوسف", "phone": "01055443322", "guardian": "01233445566", "grade": grade1},
        {"name": "مي محمود أحمد", "phone": "01144556677", "guardian": "01011223344", "grade": grade1},
        {"name": "أحمد إبراهيم حسان", "phone": "01288776655", "guardian": "01199887766", "grade": grade2},
        {"name": "سارة طارق فؤاد", "phone": "01511223344", "guardian": "01088776655", "grade": grade2},
    ]

    students = []
    for st in students_data:
        s, _ = Student.objects.get_or_create(
            name=st["name"],
            defaults={
                "phone": st["phone"],
                "guardian_phone": st["guardian"],
                "grade": st["grade"],
            }
        )
        students.append(s)
    print("✅ تم إنشاء الطلاب وتوليد أكوادهم التلقائية.")

    # 7. إلحاق الطلاب بالمجموعات (Enrollments)
    Enrollment.objects.get_or_create(student=students[0], group=g_math1) # محمد في الرياضيات
    Enrollment.objects.get_or_create(student=students[1], group=g_math1) # عمر في الرياضيات
    Enrollment.objects.get_or_create(student=students[2], group=g_math1) # مي في الرياضيات
    Enrollment.objects.get_or_create(student=students[0], group=g_arab1) # محمد في العربي
    Enrollment.objects.get_or_create(student=students[3], group=g_phys2) # أحمد في الفيزياء
    Enrollment.objects.get_or_create(student=students[4], group=g_phys2) # سارة في الفيزياء
    print("✅ تم إلحاق الطلاب بالمجموعات وتحديث سجل الحضور.")

    # 8. ضبط حالات حضور ودفع تجريبية للحصص الأخيرة
    sessions = Session.objects.all()[:5]
    for idx, sess in enumerate(sessions):
        atts = Attendance.objects.filter(session=sess)
        for i, att in enumerate(atts):
            if i % 2 == 0:
                att.status = 'present'
                att.is_paid = True
            else:
                att.status = 'present'
                att.is_paid = False  # لإنشاء ديون تجريبية
            att.save()

    print("✨ تم إنشاء وتعبئة جميع البيانات التجريبية بنجاح!")

if __name__ == '__main__':
    run()