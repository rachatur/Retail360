# IDENTITY/middleware.py

from django.db import connection
from django.conf import settings
from django.http import Http404
from django.core.exceptions import DisallowedHost
from django_tenants.middleware import TenantMiddleware as BaseTenantMiddleware
from django_tenants.utils import get_tenant_model
from django_tenants.utils import get_tenant_domain_model
from .getdomains import get_allowed_hosts

class DomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the dynamically cached allowed hosts
        domains = get_allowed_hosts()
        
        for domain in domains:
            if domain not in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS.append(domain) 
        
        # Proceed with the request
        response = self.get_response(request)
        # print(settings.ALLOWED_HOSTS)
        return response


class CustomTenantMiddleware(BaseTenantMiddleware):
    def __call__(self, request):
        # Check if the user is superuser or supportuser and manage tenant switching
        if request.user.is_authenticated and request.user.roles in ['superuser', 'supportuser', 'admin', 'posuser', 'inventoryuser']:
            selected_tenant_id = request.session.get('selected_client')
            
            if selected_tenant_id:
                try:
                    hostname = request.session.get('hostname')
                except DisallowedHost:
                    from django.http import HttpResponseNotFound
                    return HttpResponseNotFound()

                try:
                    # Get the tenant using the selected tenant ID from the session
                    tenant = get_tenant_model().objects.get(client_id=selected_tenant_id)
                    
                except get_tenant_model().DoesNotExist:
                    raise Http404("Tenant not found.")
                
                tenant.domain_url = hostname
                request.tenant = tenant
                connection.set_tenant(request.tenant)
                self.setup_url_routing(request)
            else:
                # If no tenant is selected, handle it based on your default logic, e.g., set to public schema or default tenant
                request.tenant = None
        else:
            # Let the django-tenants middleware handle the tenant resolution for regular users
            super().__call__(request)
        
        response = self.get_response(request)
        return response
