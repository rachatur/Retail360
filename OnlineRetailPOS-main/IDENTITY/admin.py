import re
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import schema_context, get_tenant_model
from import_export.admin import ImportExportModelAdmin
from rangefilter.filters import DateTimeRangeFilter
from .models import Client, Domain, User

@admin.register(Client)
class ClientAdmin(ImportExportModelAdmin):
    list_display = (
        "client_id", "client_name", "client_contact", "client_email", "client_address","client_logo", "client_currency",
        "client_type", "client_payment_mode", "client_user_count","client_allowed_user_count", "created_on",
        "created_by", "updated_on", "updated_by", "deleted_on", "deleted_by"
    )
    fields = [
        "client_name", "client_contact", "client_email", "client_address","client_allowed_user_count","client_logo", "client_currency",
        "client_type", "client_payment_mode", "deleted_on"
    ]
    exclude = ["created_on", "updated_on"]
    list_filter = (
        ("created_on", DateTimeRangeFilter), "client_id", "client_name",
        "client_contact", "client_address", "client_type"
    )
    search_fields = ["client_name"]

    def save_model(self, request, obj, form, change):
        # Set the 'created_by' field for new objects
        if not change:
            obj.created_by = request.user

        # Set the 'updated_by' and 'updated_on' fields for existing objects
        obj.updated_by = request.user
        obj.updated_on = timezone.now()

        # If 'deleted_on' is set, automatically set 'deleted_by' to the current user
        if obj.deleted_on:
            obj.deleted_by = request.user

        # Auto-generate the 'client_id' field
        total_clients = Client.objects.count()
        client_number = total_clients + 1

        # Getting the number of users with 'client_access' permission
        client_user_count = get_user_model().objects.filter(user_permissions__codename='client_access').count()
        obj.client_user_count = client_user_count
        if obj.client_id != '':
            if Client.objects.filter(client_id=obj.client_id).exists():
                self.update_tenant(request,obj, change)
        else:
            raw_client_id = f"ETHX_{obj.client_name.lower()}_{str(client_number).zfill(3)}".replace(" ", "-")
            obj.client_id = generate_valid_schema_name(raw_client_id)
            #creating the tenant and domain
            self.create_tenant(request,obj, change)

        

    def create_tenant(self, request, client, change):
        TenantModel = get_tenant_model()
        total_clients = Client.objects.count()
        client_number = total_clients + 1

        # Generate a valid schema name
        raw_schema_name = f"ETHX_{client.client_name}_{str(client_number).zfill(3)}".replace(" ", "-")
        schema_name = generate_valid_schema_name(raw_schema_name)

        # Generate a domain name
        domain_name = f"{client.client_name.lower()}.103.86.176.184".replace(" ", "-")

        # Start a transaction block to ensure atomicity
        with transaction.atomic():
            # Create the tenant
            tenant = TenantModel(
                schema_name=schema_name,
                client_id=client.client_id,
                client_name=client.client_name,
                client_contact = client.client_contact,
                client_email= client.client_email,
                client_address = client.client_address,
                client_type = client.client_type,
                client_payment_mode = client.client_payment_mode,
                client_user_count = client.client_user_count,
                client_allowed_user_count = client.client_allowed_user_count,
                client_logo = client.client_logo,
                client_currency = client.client_currency,
                updated_on = client.updated_on,
                updated_by = client.updated_by,
                created_on=timezone.now()
            )

            if not change:
                tenant.created_by = request.user

            if client.deleted_on:
                tenant.deleted_by = request.user
                tenant.deleted_on = client.deleted_on

            tenant.save()

            # Create the domain
            Domain.objects.create(
                domain=domain_name,
                tenant=tenant,
                is_primary=True
            )

            site, created = Site.objects.get_or_create(domain=domain_name, defaults={'name': client.client_name})
            # Apply migrations to the new tenant schema
            self.apply_migrations(tenant)

    def apply_migrations(self, tenant):
        """
        Apply migrations to the tenant schema.
        """
        with schema_context(tenant.schema_name):
            call_command('migrate', verbosity=1)
    
    def update_tenant(self, request, client, change):
        TenantModel = get_tenant_model()

        # Fetch the tenant associated with this client
        tenant = TenantModel.objects.filter(client_id=client.client_id).first()

        if tenant:
            # If tenant exists, update its fields
            tenant.client_name = client.client_name
            tenant.client_contact = client.client_contact
            tenant.client_email = client.client_email
            tenant.client_address = client.client_address
            tenant.client_type = client.client_type
            tenant.client_payment_mode = client.client_payment_mode
            tenant.client_user_count = client.client_user_count
            tenant.client_allowed_user_count = client.client_allowed_user_count
            tenant.client_logo = client.client_logo
            tenant.client_currency = client.client_currency
            tenant.updated_on = timezone.now()
            tenant.updated_by = request.user
            
            if client.deleted_on:
                tenant.deleted_by = request.user
                tenant.deleted_on = client.deleted_on
            else:
                tenant.deleted_by = None
                tenant.deleted_on = None

            # Save the updated tenant
            tenant.save()

            # Update the domain name if necessary
            domain_name = f"{client.client_name.lower()}.103.86.176.184".replace(" ", "-")

            domain = Domain.objects.filter(tenant=tenant).first()
            if domain:
                domain.domain = domain_name
                domain.save()

            # Apply migrations to the updated tenant schema
            self.apply_migrations(tenant)
        else:
            # If tenant doesn't exist, you might want to create it (depending on your use case)
            self.create_tenant(request, client, change)
    
    def has_delete_permission(self, request, *args):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
            
        if request.user.is_superuser or request.user.roles == 'supportuser':
            current_client = request.session.get('selected_client')
            client = request.user.clients.filter(client_id=current_client).first()
            if client.client_id == 'public':
                return queryset
            else:
               return queryset.none()  
        else:
            return queryset.none() 

        # return queryset


def generate_valid_schema_name(raw_schema_name):
    # Replace invalid characters with underscores and convert to lowercase
    schema_name = re.sub(r"[^a-z0-9_]+", "_", raw_schema_name.lower())
    # Ensure the schema name is no longer than 63 characters
    return schema_name[:63]

@admin.register(Domain)
class DomainAdmin(ImportExportModelAdmin):
    list_display = ('domain','tenant_id')
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user in ['admin','posuser', 'inventoryuser']:
            return queryset.none()  
        else:
            return queryset

    def has_add_permission(self, request, *args):
        return False

    def has_change_permission(self, request, *args):
        return False

    def has_delete_permission(self, request, *args):
        return False

    def has_import_permission(self,request, *args):
        return False
    
    def has_export_permission(self,request, *args):
        return False

@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    # Define the fields to be displayed in the list view
    list_display = ('username', 'email', 'roles', 'created_on', 'updated_on', 'designation')
    search_fields = ('username', 'email', 'roles')
    list_filter = ('roles', 'created_on', 'updated_on')
    ordering = ('-created_on',)

    # Define the fieldsets for the form layout
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'designation')}),
        ('Permissions', {'fields': ('roles','clients', 'groups', 'user_permissions',)}),
        ('Important Dates', {'fields': ('last_login',)}),
        ('Audit Info', {'fields': ('deleted_on', )}),
    )
    def get_fieldsets(self, request, obj=None):
        fieldsets = (
            (None, {'fields': ('username', 'email', 'password')}),
            ('Personal Info', {'fields': ('first_name', 'last_name', 'designation')}),
        )
        
        # Admin users should not see the permissions fieldset or have access to permissions
        if request.user.roles == 'admin':
            fieldsets += (
                ('Permissions', {'fields': ('roles', 'clients', 'groups')}),
            )
        else:
            fieldsets += (
                ('Permissions', {'fields': ('roles', 'clients', 'groups','user_permissions')}),
            )
        fieldsets += (
            ('Important Dates', {'fields': ('last_login',)}),
            ('Audit Info', {'fields': ('deleted_on',)}),
        )

        return fieldsets

    filter_horizontal = ('clients','groups','user_permissions')

    # Make the password field editable, but also be careful about how the password is set
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Hash password if it is being set (e.g., during user creation)
        if obj.roles == 'superuser':
            obj.is_superuser = True
            obj.is_staff = True
        if obj.roles == 'supportuser':
            obj.is_superuser = False
            obj.is_staff = True
        if obj.roles == 'admin':
            obj.is_superuser = False
            obj.is_staff = True
        if obj.roles in ['posuser' 'inventoryuser']:
            obj.is_superuser = False
            obj.is_staff = False

        if obj.password and obj.password != form.initial.get('password', ''):
            obj.set_password(obj.password)

        # Set created_by and updated_by fields based on the current user
        if not change:  # If it's a new object (creating)
            obj.created_by = request.user
        obj.updated_by = request.user

        # Set deleted_by if deleted_on is provided
        if obj.deleted_on:
            obj.deleted_by = request.user
        
        if not change:
            clients = form.cleaned_data.get('clients', [])
            print('Client IDS', clients,'\n')

            for client in clients:
                print('Client id', client.client_id, '\n')
                client = Client.objects.get(client_id=client.client_id)  
                print('Client',client,'\n')
                if obj.roles in ['admin', 'posuser','inventoryuser']:
                    print('roles ',obj.roles)
                    if client.client_user_count >= client.client_allowed_user_count:
                        print('raising error')
                        messages.error(request, f"Cannot assign user to client {client.client_name}. User count exceeds the allowed limit.")
                        raise ValueError(f"Cannot assign user to client {client.client_name}. User count exceeds the allowed limit.")
                    client.client_user_count += 1
                    print('client client_user_count',client.client_user_count)
                    client.save()
        
        obj.save()
    
    def has_delete_permission(self, request, *args):
        return False


        

    # Customizing the queryset based on the logged-in user's role and client(s)
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
            
        if request.user.is_superuser or request.user.roles == 'supportuser':
            current_client = request.session.get('selected_client')
            client = request.user.clients.filter(client_id=current_client).first()
            if client.client_id == 'public':
                return queryset
            elif client:
                return queryset.filter(Q(clients=client))
            else:
                return queryset.none() 

        # If the user is an admin (not superuser), restrict them to their own client's users
        if request.user.roles == 'admin':
            # Filter users by the client's association
            current_client = request.session.get('selected_client')
            client = request.user.clients.filter(client_id=current_client).first()

            if client:
                # Filter the queryset to only show users associated with that client
                return queryset.filter(
                Q(clients=client) & (Q(roles='admin') | Q(roles='posuser') | Q(roles='inventoryuser'))
            )
            else:
                return queryset.none() 
            

        # Otherwise, return the normal queryset
        return queryset
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        field = super().formfield_for_choice_field(db_field, request, **kwargs)
        
        # If the user is an admin, limit the available roles to 'admin' and 'user'
        if db_field.name == 'roles' and request.user.roles == 'admin':
            field.choices = [
                ('admin', 'Admin'),        
                ('posuser', 'Sale User'),
                ('inventoryuser', 'Inventory User'),
            ]
        
        return field

    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)

        # Filter clients for admin users based on their associated clients
        if db_field.name == 'clients' and request.user.roles == 'admin':
            queryset = field.queryset.filter(client_id__in=request.user.clients.values_list('client_id', flat=True))
            field.queryset = queryset

        # Restrict the 'groups' field to specific groups for admin users
        if db_field.name == 'groups' and request.user.roles == 'admin':
            queryset = field.queryset.filter(name__in=['Admin', 'Posuser', 'Inventoryuser'])
            field.queryset = queryset

        return field
