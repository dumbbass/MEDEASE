from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import UserProfile, Doctor, Appointment, LoginHistory, Notification, MedicalRecord, Prescription, Medication, DoctorRegistrationCode

# Register your models here.
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user_type', 'email', 'phone', 'is_active')
    list_filter = ('user_type', 'is_active')
    search_fields = ('full_name', 'user__email', 'phone')

    def email(self, obj):
        return obj.user.email

    def get_doctor_registration_link(self):
        url = reverse('register') + '?code=DOCTOR123'
        return format_html(
            '<a href="{}">Doctor Registration Link</a>',
            url
        )
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['doctor_registration_link'] = self.get_doctor_registration_link()
        return super().changelist_view(request, extra_context)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('get_doctor_name', 'specialization', 'experience', 'consultation_fee')
    search_fields = ('user_profile__full_name', 'specialization')

    def get_doctor_name(self, obj):
        return obj.user_profile.full_name
    get_doctor_name.short_description = 'Doctor Name'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
    list_filter = ('status', 'appointment_date')
    search_fields = ('patient__full_name', 'doctor__user_profile__full_name')

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'ip_address', 'is_successful')
    list_filter = ('is_successful', 'login_time')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
    search_fields = ('user__full_name', 'title', 'message')

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'record_type', 'title', 'date_created')
    list_filter = ('record_type', 'date_created')
    search_fields = ('patient__full_name', 'doctor__user_profile__full_name', 'title')

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'prescribed_date', 'status')
    list_filter = ('status', 'prescribed_date')
    search_fields = ('patient__full_name', 'doctor__user_profile__full_name')

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'name', 'dosage', 'frequency')
    search_fields = ('name', 'prescription__patient__full_name')

@admin.register(DoctorRegistrationCode)
class DoctorRegistrationCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'is_active', 'created_at', 'expires_at', 'created_by', 'get_registration_link', 'used_by')
    list_filter = ('is_active', 'created_at')
    search_fields = ('code',)
    readonly_fields = ('created_at', 'created_by')

    def get_registration_link(self, obj):
        if obj.is_active and not obj.used_by:
            url = reverse('register') + f'?code={obj.code}'
            return format_html(
                '<a href="{}" target="_blank">Registration Link</a>',
                url
            )
        return '-'
    get_registration_link.short_description = 'Registration Link'

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # If creating new code
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_changeform_initial_data(self, request):
        import random
        import string
        # Generate random code
        return {
            'code': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        }
