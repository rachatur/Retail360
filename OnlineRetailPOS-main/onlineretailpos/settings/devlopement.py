from .base import *
import os, socket
# from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv
load_dotenv()

ip_address = socket.gethostbyname(socket.gethostname())
    
DEBUG = False
SECRET_KEY = os.getenv('SECRET_KEY_DEV', 'c8ycr*3pl5tm62weh4h6+r3wgy+6*&o*d+qkdxw2s^3fay*wd=')


ALLOWED_HOSTS = ["103.86.176.184","*.103.86.176.184","subdomain.103.86.176.184","posretail360.com","www.posretail360.com","*.posretail360.com"]
CSRF_TRUSTED_ORIGINS = [f"http://{ip_address}","http://127.0.0.1","http://localhost",f"https://*.{ip_address}",f"https://{ip_address}","http://posretail360.com","https://posretail360.com","http://*.posretail360.com","https://*.posretail360.com"]

DATABASES = {
    # 'default':  database_dict[os.getenv('NAME_OF_DATABASE', 'sqlite')]
    'default':{
    # 'ENGINE': 'django.db.backends.postgresql',
    'ENGINE': 'django_tenants.postgresql_backend',
    'NAME': "OnlineRetailPOS",  # Use environment variable DB_NAME, defaulting to 'default_db_name'
    'USER': "postgres",  # Use environment variable DB_USERNAME
    'PASSWORD': "1234",  # Use environment variable DB_PASSWORD
    'HOST': "localhost",  # Use environment variable DB_HOST
    'PORT': "5432",  
    }
    
}

DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

TENANT_MODEL = "IDENTITY.Client"  # Path to your Client model
TENANT_DOMAIN_MODEL = "IDENTITY.Domain"  # Path to your Domain model

## COMMENT/UNCOMMENT to switch from  sqllite file to regular cloud database, configuration may differ
##  Database Connection

## SSH Tunnel 
# Connect to a server using the ssh keys. See the sshtunnel documentation for using password authentication
# ssh_tunnel = SSHTunnelForwarder(
#     os.getenv('SSH_HOST'),
#     ssh_username = os.getenv('SSH_USERNAME'),
#     ssh_password = os.getenv('SSH_PASSWORD'),
#     remote_bind_address=(os.getenv('SSH_DB_HOST'), 3306),
# )
# ssh_tunnel.start()


# Store Information
RECEIPT_CHAR_COUNT = int(os.getenv('RECEIPT_CHAR_COUNT', 32)) 
RECEIPT_ADDITIONAL_HEADING = os.getenv('RECEIPT_ADDITIONAL_HEADING', "")
RECEIPT_FOOTER = os.getenv('RECEIPT_FOOTER',"Thank You")


# Printer Settings
PRINTER_VENDOR_ID = os.getenv('PRINTER_VENDOR_ID', "")
PRINTER_PRODUCT_ID = os.getenv('PRINTER_PRODUCT_ID', "")
PRINT_RECEIPT = os.getenv('PRINT_RECEIPT', True)
CASH_DRAWER = os.getenv('CASH_DRAWER', False)


# For actual email sending, use Gmail's SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'retail360assist@gmail.com'  # Your Gmail address
EMAIL_HOST_PASSWORD = 'gzfo ttbj deud zaoj'  # Your Gmail password or App Password (see below)
DEFAULT_FROM_EMAIL = 'retail360assist@gmail.com'

# Set password reset timeout (optional)
PASSWORD_RESET_TIMEOUT_DAYS = 1  # The link expires in 1 day
