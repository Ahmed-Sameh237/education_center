from django.urls import path
from . import views

app_name = 'center'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    
    path('groups/', views.group_list, name='group_list'),
    path('groups/add/', views.group_add, name='group_add'),
    path('groups/<int:pk>/', views.group_detail, name='group_detail'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.teacher_add, name='teacher_add'),
    path('teachers/<int:pk>/edit/', views.teacher_edit, name='teacher_edit'),
    path('teachers/<int:pk>/', views.teacher_detail, name='teacher_detail'),
    
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/add/', views.session_add, name='session_add'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('sessions/<int:session_pk>/guest/add/', views.guest_add, name='guest_add'),
    path('sessions/generate-monthly/', views.generate_monthly_lessons_page, name='generate_monthly_lessons'),
    path('sessions/<int:pk>/status/<str:new_status>/', views.change_session_status, name='change_session_status'),

    path('setup/', views.setup_hub, name='setup_hub'),
    path('setup/grade/add/', views.grade_add, name='grade_add'),
    path('setup/grade/<int:pk>/delete/', views.grade_delete, name='grade_delete'),
    path('setup/room/add/', views.room_add, name='room_add'),
    path('setup/room/<int:pk>/delete/', views.room_delete, name='room_delete'),
    path('setup/subject/add/', views.subject_add, name='subject_add'),
    path('setup/subject/<int:pk>/delete/', views.subject_delete, name='subject_delete'),

    path('accounts/', views.center_account, name='center_account'),
    path('import-excel/', views.import_excel_students, name='import_excel'),
    path('employees/', views.employee_management, name='employee_management'),
    path('enrollments/<int:pk>/delete/', views.enrollment_delete, name='enrollment_delete'),
    path('enrollments/<int:pk>/edit-price/', views.enrollment_edit_price, name='enrollment_edit_price'),

    path('system/backup/', views.backup_restore_view, name='backup_restore'),
    path('employees/', views.employee_list_view, name='employee_list'),
    path('employees/edit/<int:pk>/', views.employee_edit_view, name='employee_edit'),
    path('employees/delete/<int:pk>/', views.employee_delete_view, name='employee_delete'),
]
