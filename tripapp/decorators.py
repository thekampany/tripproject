from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Trip, Tripper, Tribe, DayProgram, UserProfile
from functools import wraps

def tripper_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        trip = get_object_or_404(Trip, pk=kwargs['trip_id'])
        trippers = Tripper.objects.filter(trips=trip, user__isnull=False)
        
        if not trippers.filter(name=request.user.username).exists():
            return redirect('tripapp:permission_denied')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_owns_tripper(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        tripper_id = kwargs.get('tripper_id')
        
        if not tripper_id:
            #todo error_page
            return redirect('tripapp:permission_denied')

        try:
            tripper = Tripper.objects.get(id=tripper_id, user=request.user)
        except Tripper.DoesNotExist:
            return redirect('tripapp:permission_denied')

        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def is_in_tribe(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        tribes = set()

        dayprogram_id = kwargs.get("dayprogram_id")
        if dayprogram_id:
            dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)
            tribes.add(dayprogram.trip.tribe)

        trip_id = kwargs.get("trip_id")
        if trip_id:
            trip = get_object_or_404(Trip, pk=trip_id)
            tribes.add(trip.tribe)

        trip_slug = kwargs.get("slug")
        if trip_slug:
            trip = get_object_or_404(Trip, slug=trip_slug)
            tribes.add(trip.tribe)

        tribe_id = kwargs.get("tribe_id")
        if tribe_id:
            tribe = get_object_or_404(Tribe, id=tribe_id)
            tribes.add(tribe)

        extra_tribes = kwargs.get("tribes")
        if extra_tribes:
            tribes.update(extra_tribes)

        if not tribes:
            return redirect("tripapp:permission_denied")

        if not any(
            tribe.members.filter(user=request.user).exists()
            for tribe in tribes
        ):
            return redirect("tripapp:permission_denied")

        return view_func(request, *args, **kwargs)

    return _wrapped_view

def is_tripper_in_same_trip(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        
        tripper_id = kwargs.get("tripper_id")
        if tripper_id:
            tripper = get_object_or_404(Tripper, pk=tripper_id)
        else:
            return redirect("tripapp:permission_denied")

        try:
            logged_on_tripper = Tripper.objects.get(name=request.user.username, user__isnull=False)
        except Tripper.DoesNotExist:
            return redirect("tripapp:permission_denied")

        common_trips = tripper.trips.filter(id__in=logged_on_tripper.trips.all())
        
        if not common_trips.exists():
            return redirect("tripapp:permission_denied")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# logged on user has userprofile with same tribe als tripper id in kwargs for tripper_badgeassignments
def is_tripper_in_same_tribe(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        
        tripper_id = kwargs.get("tripper_id")
        if tripper_id:
            tripper = get_object_or_404(Tripper, pk=tripper_id)
        else:
            return redirect("tripapp:permission_denied")

        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return redirect("tripapp:permission_denied")

        tripper_tribes = Tribe.objects.filter(trip__trippers=tripper).distinct()
        
        common_tribe = user_profile.tribes.filter(id__in=tripper_tribes)
        
        if not common_tribe.exists():
            return redirect("tripapp:permission_denied")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view