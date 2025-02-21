from .devlopement import *
import os
from dotenv import load_dotenv
load_dotenv()

DEBUG = False
SECRET_KEY = os.getenv('SECRET_KEY_PROD','c8ycr*3pl5tm62weh4h6+r3wgy+6*&o*d+qkdxw2s^3fay*wd=')

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

# HTTPS Security - Django
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# HSTS Security - Django
SECURE_HSTS_SECONDS = 120
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


