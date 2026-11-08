from django import forms
from django.contrib.auth.models import User
from .models import Student, Teacher, Group, Session, Attendance, Room, Subject, Grade, GuestAttendance, Enrollment

class EmployeeUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'أدخل كلمة المرور'}),
        label="كلمة المرور"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'password', 'is_staff']
        labels = {
            'username': 'اسم المستخدم (للتسجيل)',
            'first_name': 'اسم الموظف / العضو',
            'is_staff': 'منح صلاحيات الإدارة (Staff)',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المستخدم'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الكامل'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'phone', 'guardian_phone', 'grade', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الطالب الثلاثي'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '01xxxxxxxxx'}),
            'guardian_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '01xxxxxxxxx'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'أي ملاحظات خاصة بالطالب'}),
        }

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['group', 'custom_price']
        widgets = {
            'group': forms.Select(attrs={'class': 'form-select'}),
            'custom_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'سعر خاص في حالة التخفيض (اختياري)'}),
        }

    def __init__(self, *args, **kwargs):
        student_grade = kwargs.pop('student_grade', None)
        super().__init__(*args, **kwargs)
        if student_grade:
            self.fields['group'].queryset = Group.objects.filter(grade=student_grade)

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['name', 'phone', 'subjects']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المعلم الثلاثي'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '01xxxxxxxxx'}),
            'subjects': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '4'}),
        }

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'subject', 'grade', 'teacher', 'room', 'day_of_week', 'time', 'session_price', 'center_cut', 'max_students']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المجموعة'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'session_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'center_cut': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['group', 'date', 'status', 'rescheduled_date', 'notes']
        widgets = {
            'group': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'rescheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'ملاحظات الحصة'}),
        }

class GuestForm(forms.ModelForm):
    class Meta:
        model = GuestAttendance
        fields = ['guest_name', 'phone', 'charged_price', 'is_paid']
        widgets = {
            'guest_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الضيف'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '01xxxxxxxxx'}),
            'charged_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الصف (مثل: الصف الأول الثانوي)'}),
        }

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'capacity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم القاعة'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '30'}),
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المادة (مثل: الفيزياء)'})}
