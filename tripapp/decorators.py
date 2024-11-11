from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Trip, Tripper
from functools import wraps

def tripper_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        trip = get_object_or_404(Trip, pk=kwargs['trip_id'])
        try:
            tripper = Tripper.objects.get(name=request.user, trips=trip)
            if not tripper:
                return redirect('tripapp:permission_denied')
        except Tripper.DoesNotExist:
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