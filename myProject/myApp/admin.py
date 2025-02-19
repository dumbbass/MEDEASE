from django.contrib import admin
from .models import UserProfile, Doctor, Appointment

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(Doctor)
admin.site.register(Appointment)
