from django.contrib import admin
from .models import Grade, Subject, Teacher, Room, Group, Student, Enrollment, Session, Attendance, GuestAttendance, Payment, TeacherPayout

admin.site.register(Grade)
admin.site.register(Subject)
admin.site.register(Teacher)
admin.site.register(Room)
admin.site.register(Group)
admin.site.register(Student)
admin.site.register(Enrollment)
admin.site.register(Session)
admin.site.register(Attendance)
admin.site.register(GuestAttendance)
admin.site.register(Payment)
admin.site.register(TeacherPayout)
