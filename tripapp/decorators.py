from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Trip, Tripper

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
