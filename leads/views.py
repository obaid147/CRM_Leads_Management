from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ActionLog, Lead, FollowUp
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import OuterRef, Subquery
from django.urls import reverse
from django.utils.http import urlencode

#---------------------------------------------------- Dashboard View
@login_required
def dashboard(request):
    """
    Dashboard view showing recent leads with latest follow-up comments
    and summary counts, using Redis caching.
    """

    query = request.GET.get('q', '')
    status = request.GET.get('status', '')

    # --- CACHE KEYS ---
    recent_cache_key = f"dashboard_recent_q={query}_status={status}"
    counts_cache_key = "dashboard_counts"

    # --- FETCH RECENT LEADS FROM CACHE ---
    recent_leads = cache.get(recent_cache_key)
    if not recent_leads:
        leads_qs = Lead.objects.filter(is_deleted=False).order_by('-id')
        if query:
            leads_qs = leads_qs.filter(
                Q(name__icontains=query) #|
                #Q(email__icontains=query) |
                #Q(phone__icontains=query)
            )
        if status:
            leads_qs = leads_qs.filter(status=status)

        # --- Get latest follow-up comment per lead ---
        latest_followup = FollowUp.objects.filter(
            lead=OuterRef('pk')
        ).order_by('-created_at')
        
        # Uses Subquery to fetch the latest follow-up comment for each lead
        # Stores this in latest_comment for easy access in the template.
        leads_qs = leads_qs.annotate(
            latest_comment=Subquery(latest_followup.values('comment')[:1])
        )

        recent_leads = leads_qs[:4]  # show only top 4 recent leads
        cache.set(recent_cache_key, recent_leads, timeout=30)  # cache for 30 seconds

    # --- FETCH SUMMARY COUNTS FROM CACHE ---
    counts = cache.get(counts_cache_key)
    if not counts:
        
        # Before optimization
        """counts = {
            'total_leads': Lead.objects.count(),
            'new_leads': Lead.objects.filter(status='new').count(),
            'in_progress_leads': Lead.objects.filter(status='in_progress').count(),
            'converted_leads': Lead.objects.filter(status='converted').count(),
            'lost_leads': Lead.objects.filter(status='lost').count(),
        }"""
        # Optimized single query for counts
        counts = Lead.objects.aggregate(
            total_leads = Count('id'),
            new_leads = Count('id', filter=Q(status='new')),
            in_progress_leads = Count('id', filter=Q(status='in_progress')),
            converted_leads = Count('id', filter=Q(status='converted')),
            lost_leads = Count('id', filter=Q(status='lost')),
        )
        cache.set(counts_cache_key, counts, timeout=30)  # cache for 30 seconds

    context = {
        'query': query,
        'status': status,
        'recent_leads': recent_leads,
        **counts
    }

    return render(request, 'leads/dashboard.html', context)

#---------------------------------------------------- Lead List View
@login_required
def lead_list(request):
    """
    View to list leads with search, filter, pagination and caching.

    Redis is used here to store query results for 60 seconds to avoid
    hitting the database repeatedly for the same search/filter parameters.
    """

    # --- GET SEARCH PARAMETERS ---
    query = request.GET.get('q', '') # capture the search term entered by user or empty string if none(default)
    status = request.GET.get('status', '') # capture the status filter selected by user or empty string if none(default)

    # --- CACHE KEY BASED ON QUERY AND STATUS ---
    # Unique key for each combination of search query and status
    cache_key = f"lead_list_q={query}_status={status}_page={request.GET.get('page', 1)}" 
    # Each different combination gets its own cache entry, so cached results don’t mix up.

    # --- TRY TO FETCH FROM CACHE ---
    page_obj = cache.get(cache_key)

    if not page_obj:  # If cache miss
        # --- FETCH FROM DATABASE ---
        leads = Lead.objects.filter(is_deleted=False).order_by('-id')  # Order by newest first

        #It returns leads where any of these fields match the search term.
        if query:
            leads = leads.filter(
                Q(name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )
        
        if status:
            leads = leads.filter(status=status)

        # --- PAGINATION ---
        paginator = Paginator(leads, 5)  # 5 leads per page
        page_number = request.GET.get('page') # store current page number from the url if not present defaults to 1
        page_obj = paginator.get_page(page_number)
        # get_page handles invalid page numbers automatically
        # get_page returns a Page object for the given 1-based page number.
        """page_obj contains:
            The leads for this page
            Pagination info (total pages, has next/previous page)"""

        # --- STORE PAGE IN CACHE ---
        # Timeout 30 seconds (we can increase later if needed)
        cache.set(cache_key, page_obj, timeout=30)

    """Prepares a context dictionary to send data to the template:
        'page_obj' → the current page of leads (for pagination in template)
        'query' → the current search term (to show in search box)
        'status' → the selected status filter (to keep it selected in the UI)"""
    context = {
        'page_obj': page_obj,
        'query': query,
        'status': status,
    }

    return render(request, 'leads/lead_list.html', context)


#---------------------------------------------------- Lead Create View
@login_required
def lead_create(request):
    if not request.user.has_perm('leads.add_lead'):
        messages.error(request, "You do not have permission to create leads.")
        return redirect('lead_list')
    """if not request.user.is_superuser:
        messages.error(request, "You do not have permission to create leads.")
        return redirect('lead_list')"""
    
    if request.method == "POST":
        name = request.POST.get('name').strip()
        email = request.POST.get('email').strip()
        phone = request.POST.get('phone').strip()

        if not name or not email or not phone:
            messages.error(request, "All fields are required.")
            return redirect("lead_create")

        if not phone.isdigit():
            messages.error(request, "Phone number must contain digits only.")
            return redirect("lead_create")

        if not len(phone) == 10:
            messages.error(request, "Phone number must be 10 digits long\nCurrent digits: " + str(len(phone)) + ".")
            return redirect("lead_create")
        
        if Lead.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return redirect("lead_create")

        lead = Lead.objects.create(name=name, email=email, phone=phone)
        messages.success(request, "Lead created successfully!")

        # Action Log for create action
        ActionLog.objects.create(
            user=request.user,
            action='create',
            lead=lead,
            comment=f"Lead created with name: {name}, email: {email}, phone: {phone}"
        )
        return redirect('lead_list')
    return render(request, 'leads/lead_create.html')

#---------------------------------------------------- Lead Update View
@login_required
def lead_update(request, pk):
    if not request.user.has_perm('leads.change_lead'):
        messages.error(request, "You do not have permission to update leads.")
        return redirect('lead_list')

    try:
        lead = Lead.objects.get(pk=pk, is_deleted=False)
    except Lead.DoesNotExist:
        messages.error(request, "Lead does not exist.")
        return redirect("lead_list")

    # original_lead = Lead.objects.get(pk=pk)  # For comparison

    if request.method == "POST":
        # Get form input
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        status = request.POST.get('status', '').strip()
        followup_text = request.POST.get('comment', '').strip()  # follow-up input

        # Validation
        if not name or not email or not phone:
            messages.error(request, "All fields are required.")
            return redirect("lead_update", pk=pk)

        if not phone.isdigit():
            messages.error(request, "Phone number must contain digits only.")
            return redirect("lead_update", pk=pk)
        
        if len(phone) != 10:
            messages.error(request, f"Phone number must be 10 digits long. Current digits: {len(phone)}.")
            return redirect("lead_update", pk=pk)

        # Check if any Lead field has changed
        lead_changed = (
            name != lead.name or
            email != lead.email or
            phone != lead.phone or
            status != lead.status
        )

        # Check if follow-up input is provided
        followup_changed = bool(followup_text)

        # If nothing changed at all
        if not lead_changed and not followup_changed:
            messages.info(request, "No changes made.")
            return redirect("lead_list")

        # Update Lead fields if changed
        if lead_changed:
            changed_fields = []
            if name != lead.name: changed_fields.append(f"name: {lead.name} -> {name}")
            if email != lead.email: changed_fields.append(f"email: {lead.email} -> {email}")
            if phone != lead.phone: changed_fields.append(f"phone: {lead.phone} -> {phone}")
            if status != lead.status: changed_fields.append(f"status: {lead.status} -> {status}")
        
            lead.name = name
            lead.email = email
            lead.phone = phone
            lead.status = status
            lead.save()

        # Audit Log for update action
            ActionLog.objects.create(
                user=request.user,
                action='update',
                lead=lead,
                comment=f"Updated fields: {', '.join(changed_fields)}"
            )

        # Create new FollowUp if provided
        if followup_changed:
            FollowUp.objects.create(
                lead=lead,
                user=request.user,
                comment=followup_text
            )
            
            # Audit Log for follow-up action
            ActionLog.objects.create(
                user=request.user,
                action='followup',
                lead=lead,
                comment=followup_text
            )

        messages.success(request, "Lead updated successfully!")
        return redirect('lead_list')

    # GET request - show form with existing data and follow-ups (if any)
    followups = FollowUp.objects.filter(lead=lead)

    return render(request, 'leads/lead_update.html', {
        'lead': lead,
        'followups': followups,
    })


"""
# Lead Update View without follow-ups
@login_required
def lead_update(request, pk):
    if not request.user.is_superuser:
        return redirect('lead_list')
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == "POST":
        lead.name = request.POST.get('name')
        lead.email = request.POST.get('email')
        lead.phone = request.POST.get('phone')
        lead.status = request.POST.get("status")
        lead.save()
        messages.success(request, "Lead updated successfully!")
        return redirect('lead_list')
    return render(request, 'leads/lead_update.html', {'lead': lead})
"""
#---------------------------------------------------- Lead Delete View
@login_required
def lead_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete leads.")
        return redirect('lead_list')
    
    try:
        lead = Lead.objects.get(pk=pk)
    except Lead.DoesNotExist:
        messages.error(request, "Lead does not exist.")
        return redirect("lead_list")
    
    if request.method == "POST":
        # Soft delete by setting is_deleted to True
        lead.is_deleted = True
        lead.save()

        # Action Log for delete action
        ActionLog.objects.create(
            user=request.user,
            action='delete',
            lead=lead,
            comment=f"Lead deleted: (Name: {lead.name}) (ID: {lead.id})"
        )

        messages.success(request, "Lead deleted successfully!")
        return redirect('lead_list')

    return render(request, 'leads/lead_delete.html', {'lead': lead})

# Logout View
def logout_view(request):
    logout(request)
    return redirect('login')

#----------------------------------------------------User Register View
def register_view(request):
    if request.method == "POST":
        username = request.POST.get('username').strip()
        password = request.POST.get('password').strip()
        confirm_password = request.POST.get('confirm_password').strip()

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')
        
        if len(password) < 5:
            messages.error(request, "Password must be at least 5 characters long")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        # Create staff user only (not superuser)
        User.objects.create_user(
            username=username, 
            password=password, 
            is_staff=True
        )
        
        messages.success(request, "Staff account created successfully!")
        
        # Redirect to login with username pre-filled
        params = urlencode({'username': username})
        login_url = reverse('login') + f'?{params}'
        return redirect(login_url)

    return render(request, 'register.html')

