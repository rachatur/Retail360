import pytz
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django_tenants.models import TenantMixin, DomainMixin
from datetime import datetime, timedelta

timezone = pytz.timezone("US/Eastern")
   
class Client(TenantMixin):
    # Primary Key
    schema_name = models.CharField(max_length=100, unique=True, null=False)
    client_id = models.CharField(max_length=50, primary_key=True, unique=True)

    # Client Information
    client_name = models.CharField(max_length=250, null=True)
    client_contact = models.PositiveBigIntegerField(null=True)  
    client_email = models.EmailField(max_length=50, null=True)
    client_address = models.CharField(max_length=500, null=True)

    # Additional Fields
    client_type = models.CharField(max_length=100, null=True)
    client_payment_mode = models.CharField(max_length=100, null=True)
    client_payment_method = models.CharField(max_length=100, null=True)
    client_user_count = models.PositiveIntegerField(null=True)
    client_allowed_user_count = models.PositiveIntegerField(null=True, default=5)
    # client_currency = MoneyField(default_currency="USD", null=True)
    client_logo = models.ImageField(upload_to='client_logos/',null=True)
    client_currency = models.CharField(max_length = 50, null=True, choices=[
        ('dollar','Dollar'),         
        ('euro','Euro'),  
        ('gbp','Pound'),      
        ('ils','Israeli New Sheqel'),  
        ('rupee','Rupee'),       
        ('jpy','YEN'),     
        ('krw','WON'),     
        ('ruble','Ruble'),        
        ('try','Turkish Lira'),         
        ])
    
    # Timestamps and Audit Fields
    created_on = models.DateField(auto_now_add=True,null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_clients', null=True
    )
    updated_on = models.DateField(auto_now=True, null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='updated_clients', null=True, blank=True
    )
    deleted_on = models.DateField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='deleted_clients', null=True, blank=True
    )

    def __str__(self):
        return self.client_name

class Domain(DomainMixin):
    pass



class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)  
    email = models.EmailField(max_length=200, unique=True, null=False)
    designation = models.CharField(max_length=100, null=True, blank=True) 
    # clients = models.ManyToManyField(Client, through='UserAccess', related_name='users') 
    clients = models.ManyToManyField(Client, related_name='users')  
    groups = models.ManyToManyField(Group, related_name='OnlineRetailPOS_users',blank=True )
    user_permissions = models.ManyToManyField(Permission, related_name='OnlineRetailPOS_users',blank=True )
   
    roles = models.CharField(max_length=50, choices=[
        ('superuser', 'Superuser'),
        ('supportuser', 'Supportuser'),
        ('admin', 'Admin'),
        ('posuser', 'Sale User'),
        ('inventoryuser', 'Inventory User'),
    ])
    
    created_on = models.DateField(auto_now_add=True,null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_users', null=True, blank=True
    )
    updated_on = models.DateField(auto_now=True, null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='updated_users', null=True, blank=True
    )
    deleted_on = models.DateField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='deleted_users', null=True, blank=True
    )



    
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    otp_timestamp = models.DateTimeField(auto_now_add=True)

    def is_otp_expired(self):
        # Convert otp_timestamp to aware datetime if it's naive
        # if timezone.is_naive(self.otp_timestamp):  # Check if it's naive
        #     self.otp_timestamp = timezone.make_aware(self.otp_timestamp, timezone)  # Make it aware

        # Get current time in the specified timezone (aware datetime)
        now = timezone.localize(datetime.now())  # Convert current time to aware datetime

        return self.otp_timestamp < now - timedelta(minutes=10)