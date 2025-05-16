from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Profile, Project, Experience, Skill, Contact, Hobby, UserProfile, Doctor, LoginHistory, Appointment, Notification, Prescription, MedicalRecord, DoctorRegistrationCode, Referral, Payment
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods, require_GET
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
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.db import models

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
    
    # Validate the code if it's provided
    valid_code = False
    if code:
        try:
            # Check if the code is in the database or settings
            valid_code = DoctorRegistrationCode.objects.filter(
                code=code,
                is_active=True,
                used_by__isnull=True
            ).exists() or code in settings.DOCTOR_REGISTRATION_CODES
        except:
            valid_code = False
    
    if request.method == 'POST':
        try:
            user_type = request.POST.get('user_type')
            admin_code = request.POST.get('admin_code')

            if user_type == 'DOCTOR':
                # For doctor registration, validate the admin code
                valid_registration_code = False
                
                try:
                    # First check the database for a valid code
                    reg_code = DoctorRegistrationCode.objects.get(
                        code=admin_code,
                        is_active=True,
                        used_by__isnull=True
                    )
                    
                    if reg_code.expires_at and reg_code.expires_at < timezone.now():
                        raise ValueError('Registration code has expired')
                    
                    valid_registration_code = True
                except DoctorRegistrationCode.DoesNotExist:
                    # If not in database, check settings
                    if admin_code in settings.DOCTOR_REGISTRATION_CODES:
                        valid_registration_code = True
                    else:
                        raise ValueError('Invalid or used registration code')
                
                if not valid_registration_code:
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
                gender = request.POST.get('gender', '')
                date_of_birth = request.POST.get('date_of_birth', '')

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
                # Save optional demographics
                if gender:
                    user_profile.gender = gender
                if date_of_birth:
                    user_profile.date_of_birth = date_of_birth
                user_profile.save()

                # Create login history entry
                LoginHistory.objects.create(
                    user=user_profile,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )

                # If user is a doctor, create Doctor profile
                if user_type == 'DOCTOR':
                    # Process available days from form
                    available_days = request.POST.get('available_days', '')
                    
                    # Create doctor record
                    doctor = Doctor.objects.create(
                        user_profile=user_profile,
                        specialization=request.POST.get('specialization', ''),
                        experience=int(request.POST.get('experience', 0) or 0),
                        qualification=request.POST.get('qualification', ''),
                        prc_license=request.POST.get('prc_license', ''),
                        consultation_fee=float(request.POST.get('consultation_fee', 0) or 0),
                        available_days=available_days,
                        available_time=request.POST.get('available_time_start', '') + ' - ' + request.POST.get('available_time_end', '')
                    )
                    
                    # If using a database registration code, mark it as used
                    try:
                        reg_code = DoctorRegistrationCode.objects.get(
                            code=admin_code,
                            is_active=True,
                            used_by__isnull=True
                        )
                        reg_code.used_by = doctor
                        reg_code.save()
                    except DoctorRegistrationCode.DoesNotExist:
                        # If using a code from settings, no need to update database
                        pass

                login(request, user)
                
                # Redirect based on user type
                if user_type == 'DOCTOR':
                    return redirect('doctor_dashboard')
                else:
                    return redirect('patient_dashboard')

        except Exception as e:
            return render(request, 'myApp/register.html', {
                'error_message': str(e),
                'code': code,
                'valid_code': valid_code
            })

    return render(request, 'myApp/register.html', {
        'code': code,
        'valid_code': valid_code
    })

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

        # Get recent referrals for the patient
        referrals = Referral.objects.filter(
            patient=user_profile
        ).order_by('-date_referred')[:5]  # Show last 5 referrals

        # Add unread notifications count
        unread_notifications_count = Notification.objects.filter(
            user=user_profile,
            is_read=False
        ).count()

        context = {
            'user_profile': user_profile,
            'appointments': appointments,
            'referrals': referrals,
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
        appointment_time = request.POST.get('appointment_time')  # Get the selected time slot
        reason = request.POST.get('reason')

        # Validate that the appointment date is not in the past
        try:
            selected_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            if selected_date < timezone.now().date():
                messages.error(request, 'Cannot book appointments in the past.')
                return redirect('book_appointment')
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('book_appointment')

        try:
            doctor = Doctor.objects.get(id=doctor_id)
            user_profile = UserProfile.objects.get(user=request.user)

            # Create the appointment with the selected time
            appointment = Appointment.objects.create(
                patient=user_profile,
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time=appointment_time,  # Use the selected time
                reason=reason,
                status='PENDING'
            )

            # Create notification for the patient
            create_notification(
                user_profile,
                'APPOINTMENT',
                'Appointment Booked',
                f'Your appointment with Dr. {doctor.user_profile.full_name} has been scheduled for {appointment_date} at {appointment_time}.',
                f'/appointments/{appointment.id}/'
            )

            messages.success(request, 'Appointment booked successfully!')
            return redirect('patient_dashboard')

        except Exception as e:
            messages.error(request, f'Error booking appointment: {str(e)}')
            return redirect('book_appointment')

    # For GET request
    doctors = Doctor.objects.all()
    # Set min_date to today's date in the correct format
    min_date = timezone.now().date().strftime('%Y-%m-%d')
    
    context = {
        'doctors': doctors,
        'min_date': min_date,
    }
    return render(request, 'myApp/book_appointment.html', context)

@login_required
def medical_history(request):
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get all appointments regardless of date or status
    all_appointments = Appointment.objects.filter(
        patient=user_profile
    ).order_by('-appointment_date')
    
    # Count different statuses for summary
    appointment_stats = {
        'total': all_appointments.count(),
        'pending': all_appointments.filter(status='PENDING').count(),
        'confirmed': all_appointments.filter(status='CONFIRMED').count(),
        'completed': all_appointments.filter(status='COMPLETED').count(),
        'cancelled': all_appointments.filter(status='CANCELLED').count()
    }
    
    return render(request, 'myApp/medical_history.html', {
        'appointments': all_appointments,
        'stats': appointment_stats
    })

@login_required
def cancel_appointment(request, appointment_id):
    if request.method == 'POST':  # Only allow POST requests
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Only allow cancellation of appointments in PENDING or CONFIRMED status
        if appointment.status in ['COMPLETED', 'CANCELLED']:
            messages.error(request, 'Cannot cancel appointments that are already completed or cancelled.')
            return redirect('patient_dashboard')
            
        if appointment.patient.user == request.user:
            appointment.status = 'CANCELLED'
            appointment.save()
            
            # Create notification for doctor
            create_notification(
                appointment.doctor.user_profile,
                'APPOINTMENT',
                'Appointment Cancelled',
                f'Patient {appointment.patient.full_name} has cancelled their appointment scheduled for {appointment.appointment_date}.',
                None
            )
            
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
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.user_type == 'PATIENT':
        # Patient view - show all their records
        records = MedicalRecord.objects.filter(patient=user_profile)
        context = {
            'records': records,
            'user_profile': user_profile,
            'is_patient': True
        }
    else:
        # Doctor view - show all records they created
        doctor = Doctor.objects.get(user_profile=user_profile)
        records = MedicalRecord.objects.filter(doctor=doctor)
        patients = UserProfile.objects.filter(patient_appointments__doctor=doctor).distinct()
        context = {
            'records': records,
            'patients': patients,
            'user_profile': user_profile,
            'doctor': doctor,
            'is_patient': False
        }
    
    return render(request, 'myApp/medical_records.html', context)

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
    user_profile = UserProfile.objects.get(user=request.user)
    
    context = {
        'prescription': prescription,
        'medications': medications,
        'user_profile': user_profile
    }
    return render(request, 'myApp/prescription_detail.html', context)

@login_required
def payments(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'PATIENT':
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('login')

        # Get all appointments with payments
        appointments = Appointment.objects.filter(
            patient=user_profile
        ).prefetch_related('payments').order_by('-appointment_date')

        # Calculate payment statistics
        total_paid = Payment.objects.filter(
            appointment__patient=user_profile,
            status='COMPLETED'
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        pending_payments = Payment.objects.filter(
            appointment__patient=user_profile,
            status='PENDING'
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        if request.method == 'POST':
            try:
                appointment_id = request.POST.get('appointment')
                amount = float(request.POST.get('amount'))
                payment_method = request.POST.get('payment_method')
                transaction_id = request.POST.get('transaction_id')
                notes = request.POST.get('notes')

                appointment = Appointment.objects.get(id=appointment_id, patient=user_profile)

                # Create payment record
                payment = Payment.objects.create(
                    appointment=appointment,
                    amount=amount,
                    payment_method=payment_method,
                    transaction_id=transaction_id if payment_method == 'ONLINE' else None,
                    processed_by=user_profile,
                    notes=notes,
                    status='PENDING'  # Payment will be confirmed by secretary
                )

                # Create notification for secretary
                secretary = UserProfile.objects.filter(user_type='SECRETARY').first()
                if secretary:
                    create_notification(
                        secretary,
                        'PAYMENT',
                        'New Payment Pending',
                        f'Patient {user_profile.full_name} has submitted a payment of ${amount} for appointment #{appointment.id}.',
                        f'/payments/{payment.id}/'
                    )

                messages.success(request, 'Payment submitted successfully! It will be processed by our staff.')
                return redirect('payments')

            except ValueError:
                messages.error(request, 'Invalid amount entered.')
            except Appointment.DoesNotExist:
                messages.error(request, 'Appointment not found.')
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')

        context = {
            'appointments': appointments,
            'total_paid': total_paid,
            'pending_payments': pending_payments,
            'user_profile': user_profile
        }
        return render(request, 'myApp/payments.html', context)

    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')

@login_required
def notifications(request):
    user_profile = UserProfile.objects.get(user=request.user)
    notifications = Notification.objects.filter(user=user_profile)
    
    context = {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count(),
        'user_profile': user_profile
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
    
    # Check if the user is a doctor
    if user_profile.user_type != 'DOCTOR':
        return redirect('login')
    
    doctor = Doctor.objects.get(user_profile=user_profile)
    
    # Get today's appointments
    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=today
    ).order_by('appointment_time')
    
    # Get recent referrals
    referrals = Referral.objects.filter(
        referring_doctor=doctor
    ).order_by('-date_referred')[:5]  # Show last 5 referrals
    
    # Get recent patients (patients with appointments)
    recent_patients = User.objects.filter(
        userprofile__patient_appointments__doctor=doctor
    ).distinct().order_by('-userprofile__patient_appointments__created_at')[:5]
    
    # Update the recent patients with additional information
    for patient in recent_patients:
        # Find the last appointment date
        last_appointment = Appointment.objects.filter(
            doctor=doctor,
            patient__user=patient
        ).order_by('-appointment_date', '-appointment_time').first()
        
        if last_appointment:
            patient.last_appointment_date = last_appointment.appointment_date
            
            # Check if the patient has upcoming appointments
            patient.has_upcoming_appointment = Appointment.objects.filter(
                doctor=doctor,
                patient__user=patient,
                appointment_date__gte=today,
                status__in=['PENDING', 'CONFIRMED']
            ).exists()
    
    # Count pending reports and referrals
    pending_reports_count = MedicalRecord.objects.filter(
        doctor=doctor,
        date_created__gte=today - timedelta(days=30)
    ).count()
    
    pending_referrals_count = Referral.objects.filter(
        referring_doctor=doctor,
        is_confirmed=False
    ).count()
    
    # Get notification count
    notification_count = Notification.objects.filter(
        user=user_profile,
        is_read=False
    ).count()
    
    context = {
        'user_profile': user_profile,
        'doctor': doctor,
        'today_appointments': today_appointments,
        'today_appointments_count': today_appointments.count(),
        'total_patients_count': Appointment.objects.filter(doctor=doctor).values('patient').distinct().count(),
        'pending_appointments': Appointment.objects.filter(doctor=doctor, status='PENDING').count(),
        'completed_appointments': Appointment.objects.filter(doctor=doctor, status='COMPLETED').count(),
        'pending_reports_count': pending_reports_count,
        'pending_referrals_count': pending_referrals_count,
        'notification_count': notification_count,
        'recent_patients': recent_patients,
        'referrals': referrals
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
            doctor.prc_license = request.POST.get('prc_license')
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

@login_required
def doctor_all_medical_history(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        doctor = Doctor.objects.get(user_profile=user_profile)
        
        # Verify that the user is a doctor
        if user_profile.user_type != 'DOCTOR':
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('login')
            
        # Get search parameters
        patient_search = request.GET.get('patient_search', '')
        status_filter = request.GET.get('status', 'all')
        
        # Get all patient appointments for this doctor
        appointments = Appointment.objects.filter(
            doctor=doctor
        ).order_by('-appointment_date')
        
        # Apply filters if provided
        if patient_search:
            appointments = appointments.filter(
                patient__full_name__icontains=patient_search
            )
            
        if status_filter != 'all' and status_filter in ['PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED']:
            appointments = appointments.filter(status=status_filter)
            
        # Get all unique patients
        patients = UserProfile.objects.filter(
            patient_appointments__doctor=doctor
        ).distinct()
        
        # Calculate statistics
        stats = {
            'total': appointments.count(),
            'pending': appointments.filter(status='PENDING').count(),
            'confirmed': appointments.filter(status='CONFIRMED').count(),
            'completed': appointments.filter(status='COMPLETED').count(),
            'cancelled': appointments.filter(status='CANCELLED').count(),
            'total_patients': patients.count()
        }
        
        context = {
            'appointments': appointments,
            'stats': stats,
            'patients': patients,
            'user_profile': user_profile,
            'doctor': doctor,
            'patient_search': patient_search,
            'status_filter': status_filter
        }
        
        return render(request, 'myApp/doctor_all_medical_history.html', context)
        
    except (UserProfile.DoesNotExist, Doctor.DoesNotExist):
        messages.error(request, 'Doctor profile not found.')
        return redirect('login')

@login_required
def admin_appointments(request):
    # Check if user is admin
    if not request.user.is_superuser:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('login')
    
    # Get filter parameters
    patient_search = request.GET.get('patient_search', '')
    patient_id = request.GET.get('patient_id', '')
    status_filter = request.GET.get('status', '')
    
    # Get all appointments
    appointments = Appointment.objects.all().order_by('-appointment_date')
    
    # Apply filters if provided
    if patient_search:
        # Search in patient name, email or phone
        appointments = appointments.filter(
            Q(patient__full_name__icontains=patient_search) |
            Q(patient__user__email__icontains=patient_search) |
            Q(patient__phone_number__icontains=patient_search)
        )
    
    if patient_id:
        # Filter by specific patient ID
        appointments = appointments.filter(patient_id=patient_id)
        
    if status_filter and status_filter in ['PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED']:
        # Filter by appointment status
        appointments = appointments.filter(status=status_filter)
    
    # Get all patients for the modal
    all_patients = UserProfile.objects.all().order_by('full_name')
    
    # Calculate statistics
    appointment_stats = {
        'total': appointments.count(),
        'pending': appointments.filter(status='PENDING').count(),
        'confirmed': appointments.filter(status='CONFIRMED').count(),
        'completed': appointments.filter(status='COMPLETED').count(),
        'cancelled': appointments.filter(status='CANCELLED').count(),
    }
    
    context = {
        'appointments': appointments,
        'all_patients': all_patients,
        'appointment_stats': appointment_stats,
        'patient_search': patient_search,
        'patient_id': patient_id,
        'status_filter': status_filter
    }
    
    return render(request, 'myApp/admin_appointments.html', context)

@login_required
def appointments_module(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        if user_profile.user_type == 'PATIENT':
            appointments = Appointment.objects.filter(patient=user_profile)
        elif user_profile.user_type == 'DOCTOR':
            doctor = Doctor.objects.get(user_profile=user_profile)
            appointments = Appointment.objects.filter(doctor=doctor)
        else:
            appointments = Appointment.objects.all()
        
        doctors = Doctor.objects.all()
        min_date = timezone.now().date()
        
        context = {
            'appointments': appointments,
            'doctors': doctors,
            'min_date': min_date,
            'user_profile': user_profile
        }
        return render(request, 'myApp/appointments_module.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found')
        return redirect('login')

@login_required
@require_POST
def confirm_appointment(request, appointment_id):
    try:
        # Get the appointment
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Get the doctor profile
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'DOCTOR':
            return JsonResponse({'status': 'error', 'message': 'Only doctors can confirm appointments'}, status=403)
            
        doctor = Doctor.objects.get(user_profile=user_profile)
        
        # Verify this is the doctor's appointment
        if appointment.doctor != doctor:
            return JsonResponse({'status': 'error', 'message': 'You can only confirm your own appointments'}, status=403)
            
        # Only allow confirming pending appointments
        if appointment.status != 'PENDING':
            return JsonResponse({'status': 'error', 'message': 'Only pending appointments can be confirmed'}, status=400)
            
        # Update appointment status
        appointment.status = 'CONFIRMED'
        appointment.save()
        
        # Create notification for patient
        create_notification(
            appointment.patient,
            'APPOINTMENT',
            'Appointment Confirmed',
            f'Dr. {doctor.user_profile.full_name} has confirmed your appointment for {appointment.appointment_date}.',
            f'/appointments/{appointment.id}/'
        )
        
        return JsonResponse({'status': 'success'})
        
    except Appointment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Appointment not found'}, status=404)
    except UserProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User profile not found'}, status=404)
    except Doctor.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Doctor profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def appointments_cancel_appointment(request, appointment_id):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Check if user has permission to cancel this appointment
        if user_profile.user_type == 'DOCTOR':
            doctor = Doctor.objects.get(user_profile=user_profile)
            if appointment.doctor != doctor:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        elif user_profile.user_type == 'PATIENT':
            if appointment.patient != user_profile:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        else:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
        # Cancel the appointment
        appointment.status = 'CANCELLED'
        appointment.save()
        
        # Create notification
        if user_profile.user_type == 'DOCTOR':
            # Notify patient
            create_notification(
                appointment.patient,
                'APPOINTMENT',
                'Appointment Cancelled',
                f'Your appointment with Dr. {user_profile.full_name} has been cancelled.',
                f'/appointments/{appointment.id}/'
            )
        else:
            # Notify doctor
            create_notification(
                appointment.doctor.user_profile,
                'APPOINTMENT',
                'Appointment Cancelled',
                f'Patient {user_profile.full_name} has cancelled their appointment scheduled for {appointment.appointment_date}.',
                f'/appointments/{appointment.id}/'
            )
            
        return JsonResponse({'status': 'success'})
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User profile not found'}, status=404)
    except Doctor.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Doctor profile not found'}, status=404)
    except Appointment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Appointment not found'}, status=404)

@login_required
@require_POST
def reschedule_appointment(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        if (request.user.user_type == 'DOCTOR' and appointment.doctor == request.user.doctor_profile) or \
           (request.user.user_type == 'PATIENT' and appointment.patient == request.user.patient_profile):
            new_date = request.POST.get('date')
            new_time = request.POST.get('time')
            if new_date and new_time:
                appointment.date = new_date
                appointment.time = new_time
                appointment.status = 'PENDING'
                appointment.save()
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'message': 'Invalid date or time'}, status=400)
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    except Appointment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Appointment not found'}, status=404)

@login_required
def doctor_calendar(request):
    # Check if user is a doctor
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'DOCTOR':
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('login')
            
        doctor = Doctor.objects.get(user_profile=user_profile)
        
        # Get date range for calendar
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date and end_date:
            # API endpoint for calendar data
            appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__range=[start_date, end_date]
            ).order_by('appointment_date', 'appointment_time')
            
            appointments_data = [{
                'id': apt.id,
                'date': apt.appointment_date.strftime('%Y-%m-%d'),
                'time': apt.appointment_time.strftime('%I:%M %p'),
                'patient_name': apt.patient.full_name,
                'reason': apt.reason,
                'status': apt.status
            } for apt in appointments]
            
            return JsonResponse({
                'status': 'success',
                'appointments': appointments_data
            })
        
        return render(request, 'myApp/doctor_calendar.html', {
            'user_profile': user_profile,
            'doctor': doctor
        })
        
    except (UserProfile.DoesNotExist, Doctor.DoesNotExist):
        messages.error(request, 'Doctor profile not found.')
        return redirect('login')

@login_required
def get_available_slots(request):
    try:
        doctor_id = request.GET.get('doctor')
        date = request.GET.get('date')
        
        if not doctor_id or not date:
            return JsonResponse({'status': 'error', 'message': 'Doctor ID and date are required'}, status=400)
            
        # Get all appointments for the selected doctor and date
        appointments = Appointment.objects.filter(
            doctor_id=doctor_id,
            appointment_date=date,
            status__in=['PENDING', 'CONFIRMED']
        )
        
        # Get booked time slots
        booked_slots = [apt.appointment_time.strftime('%H:%M') for apt in appointments]
        
        return JsonResponse({
            'status': 'success',
            'booked_slots': booked_slots
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def create_referral(request):
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.user_type != 'DOCTOR':
                messages.error(request, 'Only doctors can create referrals.')
                return redirect('doctor_dashboard')
                
            doctor = Doctor.objects.get(user_profile=user_profile)
            patient = UserProfile.objects.get(id=request.POST.get('patient'))
            
            referral = Referral.objects.create(
                patient=patient,
                referring_doctor=doctor,
                referral_type=request.POST.get('referral_type'),
                severity_level=request.POST.get('severity_level'),
                reason=request.POST.get('reason'),
                notes=request.POST.get('notes'),
                hospital_name=request.POST.get('hospital_name'),
                hospital_address=request.POST.get('hospital_address'),
                expected_duration=request.POST.get('expected_duration')
            )
            
            # Create notification for patient
            create_notification(
                patient,
                'REFERRAL',
                'New Referral Created',
                f'Dr. {doctor.user_profile.full_name} has created a referral for you.',
                f'/referrals/{referral.id}/'
            )
            
            messages.success(request, 'Referral created successfully!')
            return redirect('doctor_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error creating referral: {str(e)}')
            return redirect('create_referral')
    
    # For GET request
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'DOCTOR':
            messages.error(request, 'Only doctors can create referrals.')
            return redirect('doctor_dashboard')
            
        doctor = Doctor.objects.get(user_profile=user_profile)
        patients = UserProfile.objects.filter(
            patient_appointments__doctor=doctor
        ).distinct()
        
        return render(request, 'myApp/doctor_referral.html', {
            'patients': patients,
            'user_profile': user_profile,
            'doctor': doctor
        })
        
    except (UserProfile.DoesNotExist, Doctor.DoesNotExist):
        messages.error(request, 'Doctor profile not found.')
        return redirect('login')

@login_required
def view_referral(request, referral_id):
    try:
        referral = Referral.objects.get(id=referral_id)
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Check if user is authorized to view this referral
        if user_profile.user_type == 'DOCTOR':
            if referral.referring_doctor.user_profile != user_profile:
                messages.error(request, 'You are not authorized to view this referral.')
                return redirect('doctor_dashboard')
        else:  # Patient
            if referral.patient != user_profile:
                messages.error(request, 'You are not authorized to view this referral.')
                return redirect('patient_dashboard')
        
        return render(request, 'myApp/view_referral.html', {
            'referral': referral,
            'user_profile': user_profile
        })
        
    except Referral.DoesNotExist:
        messages.error(request, 'Referral not found.')
        return redirect('doctor_dashboard' if request.user.userprofile.user_type == 'DOCTOR' else 'patient_dashboard')

@login_required
def confirm_referral(request, referral_id):
    if request.method == 'POST':
        try:
            referral = Referral.objects.get(id=referral_id)
            user_profile = UserProfile.objects.get(user=request.user)
            
            # Only patients can confirm referrals
            if user_profile.user_type != 'PATIENT' or referral.patient != user_profile:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
                
            referral.is_confirmed = True
            referral.confirmation_date = timezone.now()
            referral.save()
            
            # Create notification for doctor
            create_notification(
                referral.referring_doctor.user_profile,
                'REFERRAL',
                'Referral Confirmed',
                f'Patient {user_profile.full_name} has confirmed your referral.',
                f'/referrals/{referral.id}/'
            )
            
            return JsonResponse({'status': 'success'})
            
        except Referral.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Referral not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def privacy_policy(request):
    return render(request, 'myApp/privacy_policy.html')

@login_required
def payment_management(request):
    # Check if user is a secretary
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'SECRETARY':
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('login')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')

    # Get filter parameters
    status_filter = request.GET.get('status', '')
    method_filter = request.GET.get('method', '')
    date_filter = request.GET.get('date', '')

    # Get all payments
    payments = Payment.objects.all().order_by('-payment_date')

    # Apply filters
    if status_filter:
        payments = payments.filter(status=status_filter)
    if method_filter:
        payments = payments.filter(payment_method=method_filter)
    if date_filter:
        payments = payments.filter(payment_date__date=date_filter)

    # Calculate payment statistics
    total_payments = payments.aggregate(total=models.Sum('amount'))['total'] or 0
    pending_payments = payments.filter(status='PENDING').aggregate(total=models.Sum('amount'))['total'] or 0
    completed_payments = payments.filter(status='COMPLETED').aggregate(total=models.Sum('amount'))['total'] or 0

    context = {
        'payments': payments,
        'total_payments': total_payments,
        'pending_payments': pending_payments,
        'completed_payments': completed_payments,
    }
    return render(request, 'myApp/payment_management.html', context)

@login_required
def process_patient_payment(request, appointment_id):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'PATIENT':
            messages.error(request, 'You are not authorized to process payments.')
            return redirect('login')

        appointment = Appointment.objects.get(id=appointment_id, patient=user_profile)
        
        if request.method == 'POST':
            try:
                amount = float(request.POST.get('amount'))
                payment_method = request.POST.get('payment_method')
                transaction_id = request.POST.get('transaction_id')
                notes = request.POST.get('notes')

                # Create payment record
                payment = Payment.objects.create(
                    appointment=appointment,
                    amount=amount,
                    payment_method=payment_method,
                    transaction_id=transaction_id if payment_method == 'ONLINE' else None,
                    processed_by=user_profile,
                    notes=notes,
                    status='PENDING'  # Payment will be confirmed by secretary
                )

                # Create notification for secretary
                secretary = UserProfile.objects.filter(user_type='SECRETARY').first()
                if secretary:
                    create_notification(
                        secretary,
                        'PAYMENT',
                        'New Payment Pending',
                        f'Patient {user_profile.full_name} has submitted a payment of ${amount} for appointment #{appointment.id}.',
                        f'/payments/{payment.id}/'
                    )

                messages.success(request, 'Payment submitted successfully! It will be processed by our staff.')
                return redirect('patient_payments')

            except ValueError:
                messages.error(request, 'Invalid amount entered.')
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')

        context = {
            'appointment': appointment,
            'user_profile': user_profile
        }
        return render(request, 'myApp/process_patient_payment.html', context)

    except (UserProfile.DoesNotExist, Appointment.DoesNotExist):
        messages.error(request, 'Appointment not found.')
        return redirect('patient_payments')

@login_required
def view_payment(request, payment_id):
    # Check if user is authorized (secretary, doctor, or patient)
    try:
        payment = Payment.objects.get(id=payment_id)
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Check authorization
        if user_profile.user_type != 'SECRETARY' and \
           user_profile != payment.appointment.patient and \
           user_profile != payment.appointment.doctor.user_profile:
            messages.error(request, 'You are not authorized to view this payment.')
            return redirect('login')
            
        context = {
            'payment': payment,
            'user_profile': user_profile
        }
        return render(request, 'myApp/view_payment.html', context)
        
    except (Payment.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, 'Payment not found.')
        return redirect('login')

@login_required
def update_payment(request, payment_id):
    # Check if user is a secretary
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'SECRETARY':
            messages.error(request, 'You are not authorized to update payments.')
            return redirect('login')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')

    if request.method == 'POST':
        try:
            payment = Payment.objects.get(id=payment_id)
            if payment.status != 'PENDING':
                messages.error(request, 'Only pending payments can be updated.')
                return redirect('payment_management')

            payment.amount = request.POST.get('amount')
            payment.payment_method = request.POST.get('payment_method')
            payment.transaction_id = request.POST.get('transaction_id')
            payment.notes = request.POST.get('notes')
            payment.status = request.POST.get('status')
            payment.save()

            # Create notification for patient
            create_notification(
                payment.appointment.patient,
                'PAYMENT',
                'Payment Updated',
                f'Your payment of ${payment.amount} has been updated.',
                f'/payments/{payment.id}/'
            )

            messages.success(request, 'Payment updated successfully!')
            return redirect('payment_management')

        except Payment.DoesNotExist:
            messages.error(request, 'Payment not found.')
            return redirect('payment_management')
        except Exception as e:
            messages.error(request, f'Error updating payment: {str(e)}')
            return redirect('payment_management')

    # For GET request
    try:
        payment = Payment.objects.get(id=payment_id)
        context = {
            'payment': payment,
            'user_profile': user_profile
        }
        return render(request, 'myApp/update_payment.html', context)
    except Payment.DoesNotExist:
        messages.error(request, 'Payment not found.')
        return redirect('payment_management')

@login_required
def patient_payments(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'PATIENT':
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('login')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')

    # Get all appointments with payments
    appointments = Appointment.objects.filter(
        patient=user_profile
    ).prefetch_related('payments').order_by('-appointment_date')

    # Calculate payment statistics
    total_paid = Payment.objects.filter(
        appointment__patient=user_profile,
        status='COMPLETED'
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    pending_payments = Payment.objects.filter(
        appointment__patient=user_profile,
        status='PENDING'
    ).aggregate(total=models.Sum('amount'))['total'] or 0

    context = {
        'appointments': appointments,
        'total_paid': total_paid,
        'pending_payments': pending_payments,
        'user_profile': user_profile
    }
    return render(request, 'myApp/patient_payments.html', context)

@login_required
def view_patient_payment(request, payment_id):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'PATIENT':
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('login')

        payment = Payment.objects.get(id=payment_id)
        if payment.appointment.patient != user_profile:
            messages.error(request, 'You are not authorized to view this payment.')
            return redirect('patient_payments')

        context = {
            'payment': payment,
            'user_profile': user_profile
        }
        return render(request, 'myApp/view_patient_payment.html', context)

    except (UserProfile.DoesNotExist, Payment.DoesNotExist):
        messages.error(request, 'Payment not found.')
        return redirect('patient_payments')

@login_required
def patient_billing_history(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.user_type != 'PATIENT':
            messages.error(request, 'You are not authorized to view this page.')
            return redirect('login')
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('login')

    # Get all payments for the patient
    payments = Payment.objects.filter(
        appointment__patient=user_profile
    ).order_by('-payment_date')

    # Calculate billing statistics
    billing_stats = {
        'total_paid': payments.filter(status='COMPLETED').aggregate(total=models.Sum('amount'))['total'] or 0,
        'pending_amount': payments.filter(status='PENDING').aggregate(total=models.Sum('amount'))['total'] or 0,
        'total_payments': payments.count(),
        'completed_payments': payments.filter(status='COMPLETED').count(),
        'pending_payments': payments.filter(status='PENDING').count(),
    }

    context = {
        'payments': payments,
        'billing_stats': billing_stats,
        'user_profile': user_profile
    }
    return render(request, 'myApp/patient_billing_history.html', context)

@require_GET
def check_username(request):
    username = request.GET.get('username', '')
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'available': not exists})

@require_GET
def check_email(request):
    email = request.GET.get('email', '')
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'available': not exists})

def terms_and_conditions(request):
    return render(request, 'myApp/terms_and_conditions.html')