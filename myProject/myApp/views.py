from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Profile, Project, Experience, Skill, Contact, Hobby, UserProfile, Doctor, LoginHistory, Appointment, Notification, Prescription, MedicalRecord, DoctorRegistrationCode
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.utils.timesince import timesince
from django.conf import settings
from django.urls import reverse

def home(request):
    # Get or create a profile
    profile, created = Profile.objects.get_or_create(
        defaults={
            'name': 'John Doe',
            'title': 'Full Stack Developer',
            'bio': 'Passionate about creating innovative web solutions'
        }
    )
    
    context = {
        'profile': profile,
        'projects': Project.objects.all(),
        'experiences': Experience.objects.all().order_by('order'),
        'skills': Skill.objects.all(),
        'contact': Contact.objects.first()
    }
    return render(request, "myApp/home.html", context)

@csrf_exempt
def save_changes(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get or create profile
            profile, created = Profile.objects.get_or_create()
            
            # Update profile fields
            profile.name = data.get('name', profile.name)
            profile.title = data.get('title', profile.title)
            profile.bio = data.get('bio', profile.bio)
            
            # Don't update the image here as it needs to be handled separately
            profile.save()

            # Update Projects
            Project.objects.all().delete()  # Clear existing projects
            for project_data in data.get('projects', []):
                Project.objects.create(
                    title=project_data['title'],
                    description=project_data['description'],
                    technologies=project_data['technologies'],
                    github_link=project_data.get('github_link', ''),
                    demo_link=project_data.get('demo_link', '')
                )

            # Update Experience
            Experience.objects.all().delete()  # Clear existing experiences
            for i, exp_data in enumerate(data.get('experiences', [])):
                Experience.objects.create(
                    title=exp_data['title'],
                    company=exp_data['company'],
                    duration=exp_data['duration'],
                    details=exp_data['details'],
                    order=i
                )

            # Update Skills
            Skill.objects.all().delete()  # Clear existing skills
            for skill_data in data.get('skills', []):
                Skill.objects.create(
                    name=skill_data['name'],
                    level=skill_data['level']
                )

            # Update Contact
            contact = Contact.objects.first()
            if not contact:
                contact = Contact()
            
            contact_data = data.get('contact', {})
            contact.email = contact_data.get('email')
            contact.phone = contact_data.get('phone')
            contact.location = contact_data.get('location')
            contact.message = contact_data.get('message')
            contact.save()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

# Add a new view for handling image uploads
@csrf_exempt
def upload_profile_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            # Get the current user's profile
            user_profile = UserProfile.objects.get(user=request.user)
            
            # Save the new image
            user_profile.profile_image = request.FILES['image']
            user_profile.save()
            
            return JsonResponse({
                'status': 'success',
                'image_url': user_profile.profile_image.url
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'No image provided'}, status=400)

@ensure_csrf_cookie
def hobby(request):
    hobbies = Hobby.objects.all()
    return render(request, 'myApp/hobby.html', {'hobbies': hobbies})

@require_http_methods(["POST"])
def save_hobbies(request):
    try:
        data = json.loads(request.body)
        hobbies_data = data.get('hobbies', [])
        
        # Delete existing hobbies
        Hobby.objects.all().delete()
        
        # Create new hobbies
        for index, hobby_data in enumerate(hobbies_data):
            Hobby.objects.create(
                title=hobby_data['title'],
                description=hobby_data['description'],
                image_url=hobby_data['image'],
                tags=hobby_data['tags'],
                order=index
            )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_http_methods(["GET"])
def get_hobbies(request):
    try:
        hobbies = Hobby.objects.all()
        hobbies_data = [{
            'title': hobby.title,
            'description': hobby.description,
            'image': hobby.image_url,
            'tags': hobby.tags
        } for hobby in hobbies]
        
        return JsonResponse({'status': 'success', 'hobbies': hobbies_data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_protect
def register_view(request):
    code = request.GET.get('code')
    if request.method == 'POST':
        try:
            user_type = request.POST.get('user_type')
            admin_code = request.POST.get('admin_code')

            if user_type == 'DOCTOR':
                try:
                    reg_code = DoctorRegistrationCode.objects.get(
                        code=admin_code,
                        is_active=True,
                        used_by__isnull=True
                    )
                    if reg_code.expires_at and reg_code.expires_at < timezone.now():
                        raise ValueError('Registration code has expired')
                except DoctorRegistrationCode.DoesNotExist:
                    raise ValueError('Invalid or used registration code')

            # Rest of your registration logic...
            with transaction.atomic():
                # Get form data
                username = request.POST['username']
                email = request.POST['email']
                password1 = request.POST['password1']
                password2 = request.POST['password2']
                full_name = request.POST['full_name']
                phone = request.POST.get('phone', '')
                address = request.POST.get('address', '')

                # Validation
                if password1 != password2:
                    raise ValueError('Passwords do not match.')

                if User.objects.filter(username=username).exists():
                    raise ValueError('Username already exists.')

                if User.objects.filter(email=email).exists():
                    raise ValueError('Email already exists.')

                # Create User first
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1
                )

                # Create UserProfile
                user_profile = UserProfile.objects.create(
                    user=user,
                    user_type=user_type,
                    full_name=full_name,
                    phone=phone,
                    address=address
                )

                # Create login history entry
                LoginHistory.objects.create(
                    user=user_profile,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )

                # If user is a doctor, create Doctor profile
                if user_type == 'DOCTOR':
                    doctor = Doctor.objects.create(
                        user_profile=user_profile,
                        specialization=request.POST.get('specialization', ''),
                        experience=int(request.POST.get('experience', 0)),
                        qualification=request.POST.get('qualification', ''),
                        consultation_fee=float(request.POST.get('consultation_fee', 0)),
                        available_days=request.POST.get('available_days', '').strip(),
                        available_time=request.POST.get('available_time', '')
                    )
                    reg_code.used_by = doctor
                    reg_code.save()

                login(request, user)
                return redirect('login')

        except Exception as e:
            return render(request, 'myApp/register.html', {
                'error_message': str(e),
                'code': code
            })

    return render(request, 'myApp/register.html', {'code': code})

@csrf_protect
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Use a different session key for regular user login
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Get user profile
            user_profile = UserProfile.objects.get(user=user)
            
            # Create login history entry
            LoginHistory.objects.create(
                user=user_profile,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            # Redirect based on user type
            if user_profile.user_type == 'DOCTOR':
                return redirect('doctor_dashboard')
            else:
                return redirect('patient_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'myApp/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def patient_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'PATIENT':
            return redirect('home')

        appointments = Appointment.objects.filter(
            patient=user_profile,
            appointment_date__gte=timezone.now().date()
        ).order_by('appointment_date', 'appointment_time')

        # Add unread notifications count
        unread_notifications_count = Notification.objects.filter(
            user=user_profile,
            is_read=False
        ).count()

        context = {
            'user_profile': user_profile,
            'appointments': appointments,
            'unread_notifications_count': unread_notifications_count
        }
        
        return render(request, 'myApp/patient_dashboard.html', context)
    
    except UserProfile.DoesNotExist:
        return redirect('login')

@login_required
def book_appointment(request):
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        appointment_date = request.POST.get('appointment_date')
        reason = request.POST.get('reason')

        try:
            doctor = Doctor.objects.get(id=doctor_id)
            user_profile = UserProfile.objects.get(user=request.user)

            # Create the appointment
            appointment = Appointment.objects.create(
                patient=user_profile,
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time='09:00',  # Default time, you can make this selectable
                reason=reason,
                status='PENDING'
            )

            # Create notification for the patient
            create_notification(
                user_profile,
                'APPOINTMENT',
                'Appointment Booked',
                f'Your appointment with Dr. {doctor.user_profile.full_name} has been scheduled for {appointment_date}.',
                f'/appointments/{appointment.id}/'
            )

            messages.success(request, 'Appointment booked successfully!')
            return redirect('patient_dashboard')

        except Exception as e:
            messages.error(request, f'Error booking appointment: {str(e)}')
            return redirect('book_appointment')

    # For GET request
    doctors = Doctor.objects.all()
    
    # If no doctors exist, create a dummy doctor
    if not doctors.exists():
        # Create dummy user if it doesn't exist
        dummy_user, created = User.objects.get_or_create(
            username='dummydoctor',
            defaults={
                'email': 'dummy@doctor.com',
            }
        )
        if created:
            dummy_user.set_password('dummypass123')
            dummy_user.save()

        # Create dummy user profile
        dummy_profile, created = UserProfile.objects.get_or_create(
            user=dummy_user,
            defaults={
                'user_type': 'DOCTOR',
                'full_name': 'Dr. John Smith'
            }
        )

        # Create dummy doctor
        doctor, created = Doctor.objects.get_or_create(
            user_profile=dummy_profile,
            defaults={
                'specialization': 'General Medicine',
                'experience': 10,
                'qualification': 'MD',
                'consultation_fee': 100.00,
                'available_days': 'Monday-Friday',
                'available_time': '9:00 AM - 5:00 PM'
            }
        )
        
        doctors = Doctor.objects.all()

    min_date = datetime.now().date()
    
    return render(request, 'myApp/book_appointment.html', {
        'doctors': doctors,
        'min_date': min_date
    })

@login_required
def medical_history(request):
    user_profile = UserProfile.objects.get(user=request.user)
    past_appointments = Appointment.objects.filter(
        patient=user_profile,
        appointment_date__lt=datetime.now().date()
    ).order_by('-appointment_date')
    
    return render(request, 'myApp/medical_history.html', {
        'appointments': past_appointments
    })

@login_required
def cancel_appointment(request, appointment_id):
    if request.method == 'POST':  # Only allow POST requests
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        if appointment.patient.user == request.user:
            appointment.status = 'CANCELLED'
            appointment.save()
            messages.success(request, 'Appointment cancelled successfully!')
        else:
            messages.error(request, 'You are not authorized to cancel this appointment.')
    
    return redirect('patient_dashboard')

@login_required
def find_doctor(request):
    search_query = request.GET.get('search', '')
    doctors = Doctor.objects.all()
    
    if search_query:
        doctors = doctors.filter(
            specialization__icontains=search_query
        )
    
    return render(request, 'myApp/find_doctor.html', {
        'doctors': doctors,
        'search_query': search_query
    })

@login_required
def delete_appointment(request, appointment_id):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        if appointment.patient.user == request.user and appointment.status == 'CANCELLED':
            appointment.delete()
            messages.success(request, 'Appointment deleted successfully!')
        else:
            messages.error(request, 'You cannot delete this appointment.')
    
    return redirect('patient_dashboard')

@login_required
def medical_records(request):
    return render(request, 'myApp/medical_records.html')

@login_required
def prescriptions(request):
    user_profile = UserProfile.objects.get(user=request.user)
    prescriptions = Prescription.objects.filter(patient=user_profile).prefetch_related('medications')
    
    context = {
        'prescriptions': prescriptions
    }
    return render(request, 'myApp/prescriptions.html', context)

@login_required
def download_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id, patient__user=request.user)
    # Add PDF generation logic here
    return JsonResponse({'status': 'error', 'message': 'Download functionality coming soon'})

@login_required
def view_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id, patient__user=request.user)
    medications = prescription.medications.all()
    
    context = {
        'prescription': prescription,
        'medications': medications
    }
    return render(request, 'myApp/prescription_detail.html', context)

@login_required
def payments(request):
    return render(request, 'myApp/payments.html')

@login_required
def notifications(request):
    user_profile = UserProfile.objects.get(user=request.user)
    notifications = Notification.objects.filter(user=user_profile)
    
    context = {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count()
    }
    return render(request, 'myApp/notifications.html', context)

@login_required
def mark_notification_read(request, notification_id):
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, user__user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(
            user__user=request.user,
            is_read=False
        ).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def profile_settings(request):
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        try:
            # Update user profile
            user_profile.full_name = request.POST.get('full_name')
            user_profile.phone = request.POST.get('phone')
            user_profile.address = request.POST.get('address')
            user_profile.blood_type = request.POST.get('blood_type')
            user_profile.allergies = request.POST.get('allergies')
            user_profile.medical_conditions = request.POST.get('medical_conditions')
            user_profile.emergency_contact_name = request.POST.get('emergency_contact_name')
            user_profile.emergency_contact_phone = request.POST.get('emergency_contact_phone')
            user_profile.save()

            # Update user email
            user_profile.user.email = request.POST.get('email')
            user_profile.user.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Profile updated successfully!'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error updating profile: {str(e)}'
            }, status=400)
    
    return render(request, 'myApp/profile_settings.html', {
        'user_profile': user_profile
    })

@login_required
def help_support(request):
    return render(request, 'myApp/help_support.html')

def create_notification(user_profile, type, title, message, related_link=None):
    return Notification.objects.create(
        user=user_profile,
        type=type,
        title=title,
        message=message,
        related_link=related_link
    )

@login_required
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check - only allow patient or doctor to view their own appointments
    if request.user != appointment.patient.user and request.user != appointment.doctor.user_profile.user:
        messages.error(request, 'You are not authorized to view this appointment.')
        return redirect('patient_dashboard')
    
    context = {
        'appointment': appointment,
        'user_profile': UserProfile.objects.get(user=request.user)
    }
    return render(request, 'myApp/appointment_detail.html', context)

@login_required
def delete_notification(request, notification_id):
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, user__user=request.user)
        notification.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def doctor_dashboard(request):
    user_profile = UserProfile.objects.get(user=request.user)
    doctor = Doctor.objects.get(user_profile=user_profile)
    
    # Get today's appointments
    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=today
    ).order_by('appointment_time')
    
    context = {
        'user_profile': user_profile,
        'doctor': doctor,
        'today_appointments': today_appointments,
        'today_appointments_count': today_appointments.count(),
        'total_patients': Appointment.objects.filter(doctor=doctor).values('patient').distinct().count(),
        'pending_appointments': Appointment.objects.filter(doctor=doctor, status='PENDING').count(),
        'completed_appointments': Appointment.objects.filter(doctor=doctor, status='COMPLETED').count(),
        'unread_notifications_count': Notification.objects.filter(user=user_profile, is_read=False).count()
    }
    
    return render(request, 'myApp/doctor_dashboard.html', context)

@login_required
def complete_appointment(request, appointment_id):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, id=appointment_id)
        doctor = Doctor.objects.get(user_profile__user=request.user)
        
        # Verify this is the doctor's appointment
        if appointment.doctor == doctor:
            appointment.status = 'COMPLETED'
            appointment.save()
            
            # Create notification for patient
            create_notification(
                appointment.patient,
                'APPOINTMENT',
                'Appointment Completed',
                f'Your appointment with Dr. {doctor.user_profile.full_name} has been marked as completed.',
                f'/appointments/{appointment.id}/'
            )
            
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def doctor_cancel_appointment(request, appointment_id):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, id=appointment_id)
        doctor = Doctor.objects.get(user_profile__user=request.user)
        
        if appointment.doctor == doctor:
            appointment.status = 'CANCELLED'
            appointment.save()
            
            # Create notification for patient
            create_notification(
                appointment.patient,
                'APPOINTMENT',
                'Appointment Cancelled',
                f'Your appointment with Dr. {doctor.user_profile.full_name} has been cancelled.',
                f'/appointments/{appointment.id}/'
            )
            
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def doctor_appointments(request):
    doctor = Doctor.objects.get(user_profile__user=request.user)
    appointments = Appointment.objects.filter(doctor=doctor).order_by('appointment_date', 'appointment_time')
    
    context = {
        'appointments': appointments,
        'user_profile': doctor.user_profile
    }
    return render(request, 'myApp/doctor_appointments.html', context)

@login_required
def doctor_patients(request):
    doctor = Doctor.objects.get(user_profile__user=request.user)
    patients = UserProfile.objects.filter(
        patient_appointments__doctor=doctor
    ).distinct()
    
    context = {
        'patients': patients,
        'user_profile': doctor.user_profile
    }
    return render(request, 'myApp/doctor_patients.html', context)

@login_required
def doctor_delete_appointment(request, appointment_id):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, id=appointment_id)
        doctor = Doctor.objects.get(user_profile__user=request.user)
        
        if appointment.doctor == doctor and appointment.status == 'CANCELLED':
            appointment.delete()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def doctor_patient_detail(request, patient_id):
    doctor = Doctor.objects.get(user_profile__user=request.user)
    patient = get_object_or_404(UserProfile, id=patient_id)
    
    # Get all appointments between this doctor and patient
    appointments = Appointment.objects.filter(
        doctor=doctor,
        patient=patient
    ).order_by('-appointment_date')
    
    # Get medical history
    medical_history = {
        'appointments': appointments,
        'total_visits': appointments.count(),
        'completed_visits': appointments.filter(status='COMPLETED').count(),
        'cancelled_visits': appointments.filter(status='CANCELLED').count(),
        'last_visit': appointments.filter(status='COMPLETED').first()
    }
    
    context = {
        'patient': patient,
        'medical_history': medical_history,
        'user_profile': doctor.user_profile
    }
    return render(request, 'myApp/doctor_patient_detail.html', context)

@login_required
def doctor_medical_records(request):
    doctor = Doctor.objects.get(user_profile__user=request.user)
    records = MedicalRecord.objects.filter(doctor=doctor)
    patients = UserProfile.objects.filter(patient_appointments__doctor=doctor).distinct()
    
    if request.method == 'POST':
        try:
            patient = UserProfile.objects.get(id=request.POST.get('patient'))
            record = MedicalRecord.objects.create(
                patient=patient,
                doctor=doctor,
                record_type=request.POST.get('record_type'),
                title=request.POST.get('title'),
                description=request.POST.get('description')
            )
            
            if request.FILES.get('file_attachment'):
                record.file_attachment = request.FILES['file_attachment']
                record.save()
            
            # Create notification for patient
            create_notification(
                patient,
                'MEDICAL_RECORD',
                f'New {record.get_record_type_display()} Added',
                f'Dr. {doctor.user_profile.full_name} has added a new medical record.',
                None
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    context = {
        'records': records,
        'patients': patients,
        'user_profile': doctor.user_profile,
        'doctor': doctor
    }
    return render(request, 'myApp/doctor_medical_records.html', context)

@login_required
def view_medical_record(request, record_id):
    doctor = Doctor.objects.get(user_profile__user=request.user)
    record = get_object_or_404(MedicalRecord, id=record_id, doctor=doctor)
    
    return JsonResponse({
        'id': record.id,
        'patient_name': record.patient.full_name,
        'record_type': record.get_record_type_display(),
        'title': record.title,
        'description': record.description,
        'date': record.date_created.strftime('%B %d, %Y'),
        'file_url': record.file_attachment.url if record.file_attachment else None
    })

@login_required
def delete_medical_record(request, record_id):
    if request.method == 'POST':
        doctor = Doctor.objects.get(user_profile__user=request.user)
        record = get_object_or_404(MedicalRecord, id=record_id, doctor=doctor)
        record.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def doctor_notifications(request):
    user_profile = UserProfile.objects.get(user=request.user)
    notifications = Notification.objects.filter(user=user_profile)
    
    context = {
        'notifications': notifications,
        'user_profile': user_profile,
        'unread_count': notifications.filter(is_read=False).count()
    }
    return render(request, 'myApp/doctor_notifications.html', context)

@login_required
def doctor_settings(request):
    doctor = Doctor.objects.get(user_profile__user=request.user)
    
    if request.method == 'POST':
        try:
            # Update doctor profile
            doctor.specialization = request.POST.get('specialization')
            doctor.experience = request.POST.get('experience')
            doctor.qualification = request.POST.get('qualification')
            doctor.consultation_fee = request.POST.get('consultation_fee')
            doctor.available_days = request.POST.get('available_days', '').strip()
            doctor.available_time = request.POST.get('available_time', '')
            doctor.save()

            # Update user profile
            doctor.user_profile.full_name = request.POST.get('full_name')
            doctor.user_profile.phone = request.POST.get('phone')
            doctor.user_profile.address = request.POST.get('address')
            doctor.user_profile.save()

            # Update user email
            doctor.user_profile.user.email = request.POST.get('email')
            doctor.user_profile.user.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Profile updated successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    context = {
        'user_profile': doctor.user_profile,
        'doctor': doctor
    }
    return render(request, 'myApp/doctor_settings.html', context)

@login_required
def generate_doctor_link(request):
    if request.user.is_superuser:
        registration_url = request.build_absolute_uri(
            reverse('register') + f'?code={settings.DOCTOR_REGISTRATION_CODES[0]}'
        )
        return JsonResponse({
            'registration_url': registration_url
        })
    return JsonResponse({'error': 'Unauthorized'}, status=403)

@login_required
def accept_appointment(request, appointment_id):
    if request.method == 'POST':
        doctor = Doctor.objects.get(user_profile__user=request.user)
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
        
        if appointment.status == 'PENDING':
            appointment.status = 'CONFIRMED'
            appointment.save()
            
            # Create notification for patient
            create_notification(
                appointment.patient,
                'APPOINTMENT',
                'Appointment Confirmed',
                f'Dr. {doctor.user_profile.full_name} has confirmed your appointment for {appointment.appointment_date}.',
                None
            )
            
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)