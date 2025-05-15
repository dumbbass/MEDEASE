from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
import os

# Create your models here.

class UserProfile(models.Model):
    USER_TYPES = [
        ('PATIENT', 'Patient'),
        ('DOCTOR', 'Doctor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='PATIENT')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    blood_type = models.CharField(max_length=5, blank=True)
    allergies = models.TextField(blank=True)
    medical_conditions = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    def get_default_profile_image(self):
        if self.user_type == 'DOCTOR':
            return 'default_images/default_doctor.png'
        return 'default_images/default_patient.png'

    def get_profile_image_url(self):
        if self.profile_image and default_storage.exists(self.profile_image.name):
            return self.profile_image.url
        return f'/media/{self.get_default_profile_image()}'

    def save(self, *args, **kwargs):
        # Capitalize the first letter of each word in full_name
        if self.full_name:
            self.full_name = ' '.join(word.capitalize() for word in self.full_name.split())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.user_type})"

    class Meta:
        db_table = 'user_profiles'
        ordering = ['-created_at']

class LoginHistory(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    is_successful = models.BooleanField(default=True)

    class Meta:
        db_table = 'login_history'
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.user.username} - {self.login_time}"

class Doctor(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    experience = models.IntegerField()
    qualification = models.CharField(max_length=200)
    prc_license = models.CharField(max_length=50, unique=True, help_text="Professional Regulation Commission License Number", null=True, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    available_days = models.CharField(max_length=200)
    available_time = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.user_profile.full_name}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    patient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='doctor_appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Appointment with Dr. {self.doctor.user_profile.full_name} on {self.appointment_date}"

class Profile(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    bio = models.TextField()
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)

class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    technologies = models.CharField(max_length=200)  # Store as comma-separated values
    github_link = models.URLField(blank=True)
    demo_link = models.URLField(blank=True)

class Experience(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    duration = models.CharField(max_length=100)
    details = models.TextField()  # Store as paragraph text
    order = models.IntegerField(default=0)  # For maintaining display order

class Skill(models.Model):
    name = models.CharField(max_length=100)
    level = models.IntegerField()  # Store as percentage

class Contact(models.Model):
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=100)
    message = models.TextField()

class Hobby(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    image_url = models.URLField(null=True, blank=True)
    tags = models.CharField(max_length=200)  # Store as comma-separated values
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-updated_at']

    def __str__(self):
        return self.title

    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('APPOINTMENT', 'Appointment'),
        ('MEDICAL_RECORD', 'Medical Record'),
        ('PRESCRIPTION', 'Prescription'),
        ('SYSTEM', 'System Message')
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_link = models.CharField(max_length=200, blank=True, null=True)  # URL to related content

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.full_name}"

class Prescription(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]
    
    patient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescribed')
    prescribed_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-prescribed_date']

class Medication(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=200)
    instructions = models.TextField()
    duration = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name} - {self.dosage}"

class MedicalRecord(models.Model):
    RECORD_TYPES = [
        ('TEST', 'Test Results'),
        ('PRESCRIPTION', 'Prescription'),
        ('DIAGNOSIS', 'Diagnosis')
    ]
    
    patient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='created_records')
    record_type = models.CharField(max_length=20, choices=RECORD_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    file_attachment = models.FileField(upload_to='medical_records/', null=True, blank=True)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.get_record_type_display()} for {self.patient.full_name}"

class DoctorRegistrationCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    used_by = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='registration_code')

    def __str__(self):
        return f"Code: {self.code} ({'Active' if self.is_active else 'Inactive'})"

class Referral(models.Model):
    REFERRAL_TYPES = [
        ('CONFINEMENT', 'Confinement'),
        ('SPECIALIST', 'Specialist Consultation'),
        ('TESTS', 'Medical Tests'),
        ('OTHER', 'Other')
    ]
    
    SEVERITY_LEVELS = [
        ('MILD', 'Mild'),
        ('MODERATE', 'Moderate'),
        ('SEVERE', 'Severe'),
        ('CRITICAL', 'Critical')
    ]
    
    patient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='referrals_received')
    referring_doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='referrals_made')
    referral_type = models.CharField(max_length=20, choices=REFERRAL_TYPES, default='CONFINEMENT')
    severity_level = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='MODERATE')
    reason = models.TextField()
    notes = models.TextField(blank=True)
    date_referred = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)
    confirmation_date = models.DateTimeField(null=True, blank=True)
    hospital_name = models.CharField(max_length=200, blank=True)
    hospital_address = models.TextField(blank=True)
    expected_duration = models.CharField(max_length=100, blank=True)  # e.g., "3-5 days"
    
    def __str__(self):
        return f"Referral for {self.patient.full_name} by Dr. {self.referring_doctor.user_profile.full_name}"
    
    class Meta:
        ordering = ['-date_referred']

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('ONLINE', 'Online Payment'),
    ]

    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='processed_payments')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} for Appointment {self.appointment.id}"
