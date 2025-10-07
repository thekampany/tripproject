

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from .models import Trip, Tripper, Badge, DayProgram, Checklist, ChecklistItem, Image, Question, Point
from .models import BingoCard, BingoAnswer, BadgeAssignment
from .models import Tribe, UserProfile, LogEntry, Link, Route, TripExpense, Location, ImmichPhotos, ScheduledItem
from .models import TripperDocument, LogEntryLike, InviteCode
from .models import TripOutline, TripOutlineItem
from .forms import BadgeForm, TripForm, ChecklistItemForm, ImageForm, BingoAnswerForm
from .forms import CustomUserCreationForm
from .forms import AnswerForm, AnswerImageForm, TripperForm, TripperAdminForm
from .forms import TribeCreationForm, AddTrippersForm, DayProgramForm
from .forms import QuestionForm, PointForm, BingoCardForm
from .forms import BadgeAssignmentFormSet, LogEntryForm
from .forms import BadgeplusQForm, QuestionplusBForm
from .forms import LinkForm, RouteForm, SuggestionForm, TripExpenseForm, TripUpdateForm, UserUpdateForm, ScheduledItemForm
from .forms import TripperDocumentForm
from .serializers import TripOutlineSerializer
from .serializers import TripSerializer, TripMapDataSerializer, LogEntryLikeSerializer


from django.contrib.auth import login, authenticate,get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .utils import get_random_unsplash_image
from django.db.models import Count, Q
from django.db.models import Prefetch

from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta, date, datetime
import uuid
from .decorators import tripper_required, user_owns_tripper
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
#from weasyprint import HTML

from django.utils.timezone import now
from django_q.tasks import async_task
from django_q.models import Task

import os
import zipfile
import base64
from django.http import FileResponse
from io import BytesIO
from PIL import Image as PILImage
from collections import Counter
from statistics import mean

from rest_framework import viewsets, status, generics
from django.contrib.auth.forms import AuthenticationForm
from rest_framework.decorators import action
from django.templatetags.static import static

import numpy as np
from rdp import rdp   

from django.db.models import F
from django.db.models.functions import Coalesce

import qrcode
import random

from django.utils.translation import gettext as _

def index(request):
    category = "roadtrip"
    background_image_url = get_random_unsplash_image(category)
    return render(request, 'tripapp/index.html', {'background_image_url': background_image_url, 'APP_NAME': settings.APP_NAME, 'VERSION':settings.VERSION,'form': AuthenticationForm()})


@login_required
def tribe_trips(request):
    user = request.user
    user_profile = request.user.userprofile
    tribes = user_profile.tribes.all()
    today = timezone.now().date()
    trips = (
        Trip.objects.filter(
            tribe__in=tribes,
            date_to__gte=today  
        )
        .order_by('-date_from', '-id')
    )

    category = "roadtrip"
    background_image_url = get_random_unsplash_image(category)
    for trip in trips:
        trip.country_codes_list = trip.country_codes.split(',') if trip.country_codes else []
    admin_trips = Trip.objects.filter(trippers__name=user, trippers__is_trip_admin=True)
    tripper = None
    if request.user.is_authenticated:
        tripper = Tripper.objects.filter(user=request.user).first()
 
    return render(request, 'tripapp/tribe_trips.html', 
        {'tribes': tribes,
         'trips': trips, 
         'background_image_url': background_image_url,
         'admin_trips': admin_trips,
         'tripper' : tripper
        })


@login_required
def invite_to_tribe(request):
    if request.method == 'POST':
        invite_type = request.POST.get('invite_type')
        tribe_id = request.POST['tribe_id']
        tribe = get_object_or_404(Tribe, id=tribe_id)

        if invite_type == "email":
            email = request.POST['email']
            current_site = request.get_host()
            current_port = request.get_port()
            invite_url = request.build_absolute_uri(
                f'/register/invite/{urlsafe_base64_encode(force_bytes(tribe_id))}/'
            )
            app_url = settings.APP_URL
            subject = 'Invitation to join a tribe'

            html_content = render_to_string('tripapp/invite_email.html', {
                'user': request.user,
                'tribe_id': tribe_id,
                'tribe_name': tribe.name,
                'domain': current_site,
                'port': current_port,
                'uid': urlsafe_base64_encode(force_bytes(tribe_id)),
                'protocol': 'https' if request.is_secure() else 'http',
                'invite_url': invite_url,
                'app_url': app_url
            })
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject, text_content, settings.DEFAULT_FROM_EMAIL, [email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

        elif invite_type == "code":
            invite = InviteCode.create_code(tribe)
            uid = urlsafe_base64_encode(force_bytes(tribe.id))

            invite_url = request.build_absolute_uri(
                reverse('tripapp:register_invite', kwargs={'uid': uid})
            )

            # QR
            qr = qrcode.QRCode(box_size=6, border=4)
            qr.add_data(invite_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer)
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()

            return render(request, "tripapp/invite_code_success.html", {
                "tribe": tribe,
                "invite_code": invite.code,
                "invite_url": invite_url,
                "qr_base64": qr_base64,
            })

        return redirect('tripapp:trip_list')

    tribes = request.user.userprofile.tribes.all()
    return render(request, 'tripapp/invite_to_tribe.html', {'tribes': tribes})

@login_required
def trip_list(request):
    user_profile = request.user.userprofile
    tribes = user_profile.tribes.all()
    trips = Trip.objects.filter(tribe__in=tribes).order_by('-date_from', '-id')
    category = "roadtrip"
    background_image_url = get_random_unsplash_image(category)
    only_mine = request.GET.get("only_mine") == "true"

    tripper = None
    if request.user.is_authenticated:
        tripper = Tripper.objects.filter(user=request.user).first()
        for trip in trips:
            trip.is_tripper = tripper in trip.trippers.all()
    else:
        for trip in trips:
            trip.is_tripper = False
    

    for trip in trips:
        trip.country_codes_list = trip.country_codes.split(',') if trip.country_codes else []

    return render(request, 'tripapp/trip_list.html', {'tribes': tribes, 'trips': trips, 'background_image_url': background_image_url, 'tripper':tripper,"only_mine": only_mine})

@login_required
def trip_detail(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    dayprograms = DayProgram.objects.filter(trip=trip).order_by('tripdate')
    checklist = Checklist.objects.get_or_create(trip=trip)[0]
    checklist_items = ChecklistItem.objects.filter(checklist=checklist).order_by('is_completed', 'id')  # Sorteer op is_completed en vervolgens op id
    items = checklist.items.all()
    today = date.today()
    tripper = None
    if request.user.is_authenticated:
        tripper = Tripper.objects.filter(user=request.user).first()
    view_mode = request.GET.get("view", "list")

    return render(request, 'tripapp/trip_detail.html', {
        'trip': trip,
        'dayprograms': dayprograms,
        'checklist': checklist,
        'items': checklist_items,
        'today': today,
        'tripper': tripper,
        'view_mode': view_mode
    })

@login_required
def create_trip(request, tribe_id):
    tribe = get_object_or_404(Tribe, pk=str(tribe_id))
    if request.method == 'POST':
        form = TripForm(request.POST,user=request.user)
        if form.is_valid():
            trip = form.save()
            date_from = trip.date_from
            date_to = trip.date_to
            current_date = date_from
            daynumber =1

            # Create DayProgram entries for each day in the trip
            while current_date <= date_to:
                DayProgram.objects.create(trip=trip, tripdate=current_date, dayprogramnumber=daynumber)
                current_date += timedelta(days=1)
                daynumber += 1

            # Ensure the logged-in user is also a Tripper for this trip
            user = request.user
            tripper, created = Tripper.objects.get_or_create(user=user, defaults={'name': user.username})
            tripper.trips.add(trip)
            tripper.is_trip_admin = True
            tripper.save()


            return redirect('tripapp:tribe_trips')
    else:
        form = TripForm(user=request.user, tribe=tribe)
    return render(request, 'tripapp/create_trip.html', {'form': form})

@login_required
def trip_trippers(request, id):
    trip = get_object_or_404(Trip, pk=id)
    trippers = trip.trippers.annotate(
        badge_count=Count('badge_assignments', filter=Q(badge_assignments__trip=trip)),
        total_badge_count=Count('badge_assignments') 
    ).order_by('-badge_count', '-total_badge_count')

    return render(request, 'tripapp/trip_trippers.html', {'trip': trip, 'trippers': trippers})

@login_required
def upload_badge(request):

    user = request.user
    user_profile = user.userprofile
    tribes = user_profile.tribes.all()

    if request.method == 'POST':
        form = BadgeForm(request.POST, request.FILES)
        form.fields['tribe'].queryset = tribes  
        if form.is_valid():
            badge = form.save(commit=False)
            badge.save()
            return redirect('tripapp:trip_list')
        else:
            print(form.errors)

    else:
        form = BadgeForm()
        form.fields['tribe'].queryset = tribes

    return render(request, 'tripapp/upload_badge.html', {'form': form})


@login_required
def tripper_badgeassignments(request, tripper_id):
    tripper = get_object_or_404(Tripper, id=tripper_id)
    badge_assignments = BadgeAssignment.objects.filter(tripper=tripper).select_related('badge', 'trip').order_by(F('trip__id').desc(nulls_last=True))
    badges = [assignment.badge for assignment in badge_assignments]
    count_tripper_badges = BadgeAssignment.objects.filter(tripper=tripper).count()
    return render(request, 'tripapp/tripper_badgeassignments.html', {'tripper': tripper, 'badges': badges, 'count_tripper_badges':count_tripper_badges})


@login_required
def trip_tripper_badgeassignments(request, trip_id, tripper_id):
    trip = get_object_or_404(Trip, id=trip_id)
    tripper = get_object_or_404(Tripper, id=tripper_id)
    badge_assignments = BadgeAssignment.objects.filter(trip=trip, tripper=tripper).select_related('badge')
    badges = [assignment.badge for assignment in badge_assignments]
    return render(request, 'tripapp/trip_tripper_badgeassignments.html', {'trip': trip, 'tripper': tripper, 'badges': badges})

@login_required
def dayprogram_detail(request, id):
    dayprogram = get_object_or_404(DayProgram, id=id)
    questions = Question.objects.filter(dayprogram=dayprogram).all()
    form = AnswerForm() if request.user.is_authenticated else None
    suggestionform = SuggestionForm() if request.user.is_authenticated else None
    images = dayprogram.images.all()
    trippers_on_this_trip = dayprogram.trip.trippers.all()
    trippers_names = [tripper.name for tripper in trippers_on_this_trip]

    log_entries = dayprogram.logentries.all()
    logentry_ids = [le.id for le in log_entries]
    likes = LogEntryLike.objects.filter(logentry_id__in=logentry_ids).select_related('tripper')

    likes_per_logentry = {}
    for like in likes:
        likes_per_logentry.setdefault(like.logentry_id, []).append(like)

    for le in log_entries:
        le.likes_list = likes_per_logentry.get(le.id, [])
        le.likes_display = [f"{like.tripper.name} {like.emoji}" for like in le.likes_list]

        counts = Counter([like.emoji for like in le.likes_list])
        le.emoji_counts = dict(counts)

    emoji_options = ["👍", "❤️", "🔥", "😂", "🎉","💪","🤩","😱"]

    logged_on_tripper = Tripper.objects.filter(name=request.user.username).first()

    previous_dayprogram = DayProgram.objects.filter(
        trip=dayprogram.trip,
        dayprogramnumber__lt=dayprogram.dayprogramnumber
    ).order_by('-dayprogramnumber').first()

    next_dayprogram = DayProgram.objects.filter(
        trip=dayprogram.trip, 
        dayprogramnumber__gt=dayprogram.dayprogramnumber
    ).order_by('dayprogramnumber').first()

    questions_with_badge_info = []
    for question in questions:
        question_info = {
            'question': question,
            'trippers_badge_info': []
        }
        for tripper in trippers_on_this_trip:
            has_badge = BadgeAssignment.objects.filter(
                tripper=tripper, 
                badge=question.badge
            ).exists()
            question_info['trippers_badge_info'].append({
                'tripper': tripper,
                'has_badge': has_badge
            })
        questions_with_badge_info.append(question_info)

    badge_id = request.GET.get('badge')
    badge = None
    if badge_id:
        badge = Badge.objects.filter(pk=badge_id).first()

    links_without_scheduled_item = dayprogram.links.filter(scheduled_item__isnull=True)
    links_with_scheduled_item = dayprogram.links.filter(scheduled_item__isnull=False)
    scheduled_items = dayprogram.scheduled_items.all().order_by('start_time')

    # -------- Weather --------
    weather_forecast_data = None
    if dayprogram.tripdate in [ date.today() + timedelta(days=i) for i in range(0, 4)]:
        points = dayprogram.points.all()
        if points.exists():
            lat = sum(p.latitude for p in points) / len(points)
            lon = sum(p.longitude for p in points) / len(points)

            trip_date = dayprogram.tripdate

            # Open-Meteo API
            base_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&hourly=temperature_2m,weather_code"
                f"&timezone=Europe%2FBerlin"
                f"&start_date={trip_date}&end_date={trip_date}"
            )

            if settings.TEMPERATURE_UNIT == 'F':
                base_url += "&temperature_unit=fahrenheit"

            try:
                response = requests.get(base_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    times = data["hourly"]["time"]
                    weather_codes = data["hourly"]["weather_code"]
                    temperatures = data["hourly"]["temperature_2m"]

                    if weather_codes:
                        avg_code = round(mean(weather_codes))
                        max_code = max(weather_codes)
                        most_common_code = Counter(weather_codes).most_common(1)[0][0]
                        max_temp = max(temperatures)

                        weather_forecast_data = {
                            "date": trip_date.isoformat(),
                            "weather_code_avg": avg_code,
                            "weather_code_max": max_code,
                            "weather_code_mode": most_common_code,
                            "temperature_max": max_temp,
                         }
            except Exception as e:
                print(f"Error retrieving weather: {e}")
    # -------- End Weather --------

    return render(request, 'tripapp/dayprogram_detail.html', 
         {'dayprogram': dayprogram, 
          'images': images, 
          'questions': questions,
          'questions_with_badge_info': questions_with_badge_info,
          'form': form,
          'suggestionform':suggestionform,
          'today': timezone.now().date(),
          'trippers_names': trippers_names,
          'log_entries': log_entries,
          'emoji_options': emoji_options,
          'previous_dayprogram' : previous_dayprogram,
          'next_dayprogram' : next_dayprogram,
          'logged_on_tripper' : logged_on_tripper,
          'links_without_scheduled_item' : links_without_scheduled_item,
          'links_with_scheduled_item' : links_with_scheduled_item,
          'scheduled_items' : scheduled_items,
          'weather_forecast_data' : weather_forecast_data,
          'badge_overlay': badge,
         })


@login_required
def add_image(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    if request.method == 'POST':
        files = request.FILES.getlist('images')
        for file in files:
            Image.objects.create(day_program=dayprogram, image=file)
        return redirect('tripapp:dayprogram_detail', id=dayprogram_id)

    form = ImageForm(initial={'day_program': dayprogram})
    return render(request, 'tripapp/add_image.html', {'form': form, 'dayprogram': dayprogram})

@login_required
def add_or_edit_trip(request, id=None):
    if id:
        trip = get_object_or_404(Trip, id=id)
    else:
        trip = None

    if request.method == 'POST':
        form = TripForm(request.POST, request.FILES, instance=trip)
        if form.is_valid():
            form.save()
            return redirect('tripapp:trip_detail', id=form.instance.id)
    else:
        form = TripForm(instance=trip)

    return render(request, 'tripapp/add_or_edit_trip.html', {'form': form})

@login_required
def add_checklist_item(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    checklist = Checklist.objects.get_or_create(trip=trip)[0]

    if request.method == 'POST':
        form = ChecklistItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.checklist = checklist
            item.save()
            return redirect('tripapp:trip_detail', trip.slug)
    else:
        form = ChecklistItemForm()

    return render(request, 'tripapp/add_checklist_item.html', {'form': form, 'trip': trip})

@login_required
def toggle_checklist_item(request, item_id):
    item = get_object_or_404(ChecklistItem, id=item_id)
    item.is_completed = not item.is_completed
    item.save()
    return redirect('tripapp:trip_detail', item.checklist.trip.slug)


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('tripapp:tribe_trips')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def check_answer(request, id, questionid):
    dayprogram = get_object_or_404(DayProgram, id=id)
    question = get_object_or_404(Question, id=questionid)

    if question is None:
        return redirect('tripapp:dayprogram_detail', id=dayprogram.id)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.cleaned_data['answer']
            if answer.lower() in question.correct_answer.lower():
                current_user = request.user
                tripper = Tripper.objects.filter(name=current_user.username).first()
                tripper.badges.add(question.badge)
                BadgeAssignment.objects.create(tripper=tripper, badge=question.badge, trip=dayprogram.trip)

                url = reverse('tripapp:dayprogram_detail', args=[dayprogram.id])
                return redirect(f"{url}?badge={question.badge.id}")
            else:
                return redirect('tripapp:dayprogram_detail', id=dayprogram.id)

    return redirect('tripapp:dayprogram_detail', id=dayprogram.id)

@login_required
def badge_claimed(request, badge_id):
    badge = get_object_or_404(Badge, pk=badge_id)
    return render(request, 'tripapp/badge_claimed.html', {'badge': badge})

@login_required
def badge_list(request):
    badges = Badge.objects.all()
    return render(request, 'tripapp/badge_list.html', {'badges': badges})


@login_required
def mytribes_badges_view(request):
    user = request.user
    user_profile = user.userprofile
    tribes = user_profile.tribes.all()
    tribal_badges = Badge.objects.filter(level='tribal', tribe__in=tribes)
    global_badges = Badge.objects.filter(level='global')

    return render(request, 'tripapp/mytribes_badges.html', {
        'global_badges': global_badges,
        'tribal_badges': tribal_badges,
    })



def get_country_coords(country_code):
    url = f"https://nominatim.openstreetmap.org/search?country={country_code}&format=json&limit=1"
    response = requests.get(url, headers={'User-Agent': 'trip-planner-app'})
    
    if response.status_code == 200:
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    
    return None  


@login_required
def trip_map_view(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    points = trip.points.prefetch_related('dayprograms')

    start_of_day = timezone.make_aware(datetime.combine(trip.date_from, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(trip.date_to, datetime.max.time()))
    trippers = trip.trippers.all()

    all_locations = Location.objects.filter(
        tripper__in=trippers,
        timestamp__range=(start_of_day, end_of_day)
    ).order_by('timestamp')

    # Simplify
    coords = np.array([[loc.latitude, loc.longitude] for loc in all_locations])
    simplified_coords = coords
    if len(coords) > 0:
        if len(coords) > 10000:
            step = len(coords) // 10000
            coords = coords[::step]

        if len(coords) > 150:
            simplified_coords = rdp(coords, epsilon=0.001)  # 100 meter
        else:
            simplified_coords = coords

    simplified_locations = []
    latlon_set = {(float(lat), float(lon)) for lat, lon in simplified_coords}
    for loc in all_locations:
        key = (float(loc.latitude), float(loc.longitude))
        if key in latlon_set:
            simplified_locations.append(loc)
            latlon_set.remove(key)  

    photolocations = ImmichPhotos.objects.filter(
        tripper__in=trippers,
        timestamp__range=(start_of_day, end_of_day)
    )

    first_country_code = trip.get_first_country_code()
    country_coords = get_country_coords(first_country_code) if first_country_code else get_country_coords('nl')

    return render(request, 'tripapp/trip_map.html', {
        'trip': trip,
        'points': points,
        'locations': simplified_locations,  
        'photolocations': photolocations,
        'locations_truncated': len(all_locations) > len(simplified_locations),
        'max_locations': min(len(all_locations), len(simplified_locations)),
        'country_coords': country_coords,
    })


@login_required
def tribe_map_view(request, tribe_id):
    tribe = get_object_or_404(Tribe, id=tribe_id)
    trips = Trip.objects.filter(tribe=tribe)

    trip_locations = []
    for trip in trips:
        code = trip.get_first_country_code()
        coords = get_country_coords(code) if code else get_country_coords('nl')
        if coords:  
            photo_url = trip.image.url if trip.image else static('favicon/apple-touch-icon.png')
            trip_locations.append({
                'name': trip.name,
                'latitude': coords[0],
                'longitude': coords[1],
                'photo_url': photo_url,
                'trip_url': reverse('tripapp:trip_detail', kwargs={'slug': trip.slug}),
            })
    return render(request, 'tripapp/tribe_map.html', {
        'tribe': tribe,
        'trip_locations': trip_locations,
    })

def convert_to_float(value):
    try:
        return float(value.replace(',', '.')) if isinstance(value, str) else float(value)
    except ValueError:
        raise ValidationError(f"No valid float: {value}")


@login_required
def trip_dayprogram_points(request, trip_id, dayprogram_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    trippers = trip.trippers.all()
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    trip_points = Point.objects.filter(trip=trip)

    points = trip_points.filter(dayprograms=dayprogram)
 
    filter_date = dayprogram.tripdate
    start_of_day = timezone.make_aware(datetime.combine(filter_date, datetime.min.time()))
    end_of_day = start_of_day + timedelta(days=1)
    locations = Location.objects.filter(tripper__in=trippers,timestamp__range=(start_of_day, end_of_day)).order_by("timestamp")
    photolocations = ImmichPhotos.objects.filter(tripper__in=trippers,timestamp__range=(start_of_day, end_of_day)).order_by("timestamp")
    
    trip_name_no_spaces = trip.name.replace(" ", "")
    tribe_name_no_spaces = trip.tribe.name.replace(" ","")
    first_point = points.first() if points.exists() else None

    first_country_code = trip.get_first_country_code() 
    country_coords = get_country_coords(first_country_code) if first_country_code else None

    previous_dayprogram = DayProgram.objects.filter(
        trip=dayprogram.trip,
        dayprogramnumber__lt=dayprogram.dayprogramnumber
    ).order_by('-dayprogramnumber').first()

    next_dayprogram = DayProgram.objects.filter(
        trip=dayprogram.trip, 
        dayprogramnumber__gt=dayprogram.dayprogramnumber
    ).order_by('dayprogramnumber').first()


    context = {
        'trip': trip,
        'dayprogram': dayprogram,
        'points': points,
        'trip_name_no_spaces':trip_name_no_spaces,
        'tribe_name_no_spaces' : tribe_name_no_spaces,
        'first_point': first_point,
        'locations': locations,
        'photolocations': photolocations,
        'country_coords': country_coords,
        'previous_dayprogram' : previous_dayprogram,
        'next_dayprogram' : next_dayprogram,
    }

    return render(request, 'tripapp/trip_dayprogram_points.html', context) 


@tripper_required
def trip_tripper_bingocard(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    bingocards = trip.bingocards.all()
    bingo_answers = BingoAnswer.objects.filter(bingocard__in=bingocards)
    user_answers = BingoAnswer.objects.filter(tripper__name=request.user)
    user_answered_cards_ids = set(user_answers.values_list('bingocard_id', flat=True))
    trippers_on_this_trip = trip.trippers.annotate(
        answer_count=Count('bingoanswer', filter=Q(bingoanswer__bingocard__trip=trip))
    ).order_by('-answer_count')
    trippers_names = [tripper.name for tripper in trippers_on_this_trip]


    return render(request, 'tripapp/trip_bingocard.html', {
        'trip': trip,
        'bingocards': bingocards,
        'user_answers': user_answers,
        'bingo_answers': bingo_answers,
        'user_answered_cards_ids': user_answered_cards_ids,
        'trippers_names': trippers_names,
        'trippers_on_this_trip': trippers_on_this_trip,  
         })

@login_required
def trip_bingocards(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    bingocards = trip.bingocards.all()
    bingo_answers = BingoAnswer.objects.filter(bingocard__in=bingocards)
    user_answers = BingoAnswer.objects.filter(tripper__name=request.user)
    user_answered_cards_ids = set(user_answers.values_list('bingocard_id', flat=True))
    trippers_on_this_trip = trip.trippers.all()
    trippers_names = [tripper.name for tripper in trippers_on_this_trip]


    return render(request, 'tripapp/trip_bingocards.html', {
        'trip': trip,
        'bingocards': bingocards,
        'user_answers': user_answers,
        'bingo_answers': bingo_answers,
        'user_answered_cards_ids': user_answered_cards_ids,
        'trippers_names': trippers_names,
         })


@login_required
def bingocard_detail(request, pk):
    bingocard = get_object_or_404(BingoCard, pk=pk)
    return render(request, 'tripapp/bingocard_detail.html', {'bingocard': bingocard})

@login_required
def upload_answerimage(request, bingocard_id):
    bingocard = get_object_or_404(BingoCard, pk=bingocard_id)
    tripper = get_object_or_404(Tripper, name=request.user)

    answer = BingoAnswer.objects.filter(tripper=tripper, bingocard=bingocard).first()

    if request.method == 'POST':
        if answer is None:
            answer = BingoAnswer(tripper=tripper, bingocard=bingocard)
            created = True
        else:
            created = False

        form = BingoAnswerForm(request.POST, request.FILES, instance=answer)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.tripper = tripper
            answer.bingocard = bingocard
            answer.save()
            trip_answer_count = answer.count_trip_answers()
            badges = Badge.objects.filter(achievement_method='threshold')
            for badge in badges:
                if badge.threshold_type == 'bingo_answer_uploads':
                   trip_answer_count = BingoAnswer.objects.filter(
                      tripper=tripper,
                      bingocard__trip=bingocard.trip
                   ).count()

                if trip_answer_count >= badge.threshold_value:
                    if not BadgeAssignment.objects.filter(tripper=tripper, badge=badge, trip=bingocard.trip).exists():
                        BadgeAssignment.objects.create(tripper=tripper, badge=badge, trip=bingocard.trip)
                        tripper.badges.add(badge)

            return redirect('tripapp:trip_tripper_bingocard',trip_id=bingocard.trip.id) 
    else:
        form = BingoAnswerForm(instance=answer)
        created = False
    return render(request, 'tripapp/upload_answerimage.html',{'form': form, 'bingocard': bingocard, 'answer': answer, 'created': created})

@user_owns_tripper
def tripper_profile(request, tripper_id):
    tripper = get_object_or_404(Tripper, id=tripper_id)
    documents = TripperDocument.objects.filter(tripper=tripper)  

    if request.method == 'POST':
        form = TripperForm(request.POST, request.FILES, instance=tripper)
        if form.is_valid():
            form.save()
            return redirect('tripapp:tripper_profile', tripper_id=tripper.id)
    else:
        form = TripperForm(instance=tripper)
    return render(request, 'tripapp/tripper_profile.html', 
                {'form': form, 
                'tripper': tripper,
                'documents': documents,
                'document_form': TripperDocumentForm()
                })

@login_required
def assign_badge(request, tripper_id, badge_id, trip_id=None):
    tripper = get_object_or_404(Tripper, pk=tripper_id)
    badge = get_object_or_404(Badge, pk=badge_id)
    trip = None
    if trip_id:
        trip = get_object_or_404(Trip, pk=trip_id)
    BadgeAssignment.objects.create(tripper=tripper, badge=badge, trip=trip)

    tripper.badges.add(badge)

    return redirect('tripapp:trip_tripper_badges', trip_id= trip_id, tripper_id = tripper_id )


@login_required
def register_invite(request, uid):
    tribe_id = force_str(urlsafe_base64_decode(uid))
    tribe = get_object_or_404(Tribe, id=tribe_id)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            if not UserProfile.objects.filter(user=user).exists():
                user_profile, created = UserProfile.objects.get_or_create(user=user)
                user_profile.tribes.add(tribe)
                user_profile.save()
            else:
                user_profile = UserProfile.objects.get(user=user)
                user_profile.tribes.add(tribe)
                user_profile.save()
            return redirect('tripapp:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'tripapp/register_invite.html', {'form': form, 'tribe': tribe})


@login_required
def create_tribe(request):
    if request.method == 'POST':
        form = TribeCreationForm(request.POST)
        if form.is_valid():
            tribe = form.save(commit=False)
            tribe.save()
            user_profile = request.user.userprofile
            user_profile.tribes.add(tribe)
            return redirect('tripapp:tribe_trips')
    else:
        form = TribeCreationForm()
    tribes = request.user.userprofile.tribes.all()
    return render(request, 'tripapp/create_tribe.html', {'form': form, 'tribes': tribes})

@login_required
def add_trippers(request, trip_id, tribe_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    tribe = get_object_or_404(Tribe, pk=str(tribe_id))

    if request.method == 'POST':
        form = AddTrippersForm(request.POST, tribe=tribe)
        if form.is_valid():
            users = form.cleaned_data['users']
            trippers = trip.trippers.all()
            for user in users:
                tripper, created = Tripper.objects.get_or_create(name=user)
                tripper.trips.add(trip)
            for tripper in trippers.exclude(name__in=[user.username for user in users]):
                tripper.trips.remove(trip)
            return redirect('tripapp:tribe_trips')
    else:
        form = AddTrippersForm(tribe=tribe, trip=trip)


    return render(request, 'tripapp/add_trippers.html', {
        'form': form,
        'trip': trip,
        'tribe': tribe,
    })


@login_required
def edit_tripper(request, tripper_id, trip_id):
    tripper = get_object_or_404(Tripper, id=tripper_id)
    trip = get_object_or_404(Trip, id=trip_id)

    if request.method == 'POST':
        form = TripperAdminForm(request.POST, request.FILES, instance=tripper)
        formset = BadgeAssignmentFormSet(
            request.POST,
            instance=tripper,
            queryset=BadgeAssignment.objects.filter(trip=trip,tripper=tripper),
            trip=trip,
            tripper=tripper
        )
        if form.is_valid() and formset.is_valid():
            form.save()
            instances = formset.save(commit=False)
            for instance in instances:
                instance.trip = trip
                instance.save()
            formset.save_m2m()
            return redirect('tripapp:tribe_trips')
    else:
        form = TripperAdminForm(instance=tripper)
        formset = BadgeAssignmentFormSet(
            instance=tripper,
            queryset=BadgeAssignment.objects.filter(trip=trip,tripper=tripper),
            trip=trip,
            tripper=tripper
        )

    return render(request, 'tripapp/edit_tripper.html', {
        'form': form,
        'formset': formset,
        'tripper': tripper,
        'trip': trip
    })

@login_required
def tripper_list(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    trippers = trip.trippers.all()
    return render(request, 'tripapp/tripper_list.html', {'trip': trip, 'trippers': trippers})



@login_required
def edit_dayprogram(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    trip = dayprogram.trip

    if request.method == 'POST':
        form = DayProgramForm(request.POST, instance=dayprogram, trip=trip)
        if form.is_valid():
            form.save()
            return redirect('tripapp:trip_dayprograms', trip_id=dayprogram.trip.id)
    else:
        form = DayProgramForm(instance=dayprogram, trip=trip)
    return render(request, 'tripapp/edit_dayprogram.html', {
        'form': form,
        'dayprogram': dayprogram,
    })

@login_required
def trip_dayprograms(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    dayprograms = trip.dayprograms.all().order_by('dayprogramnumber')
    user_is_tripper = Tripper.objects.filter(name=request.user, trips=trip).exists()
    admin_trips = Trip.objects.filter(trippers__name=request.user, trippers__is_trip_admin=True)

    return render(request, 'tripapp/trip_dayprograms.html', {
        'trip': trip,
        'dayprograms': dayprograms,
        'user_is_tripper': user_is_tripper,
        'admin_trips' : admin_trips
    })


@login_required
def add_question(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.dayprogram = dayprogram
            question.save()
            return redirect('tripapp:dayprogram_questions', dayprogram_id=dayprogram.id)
    else:
        form = QuestionForm(dayprogram=dayprogram)

    return render(request, 'tripapp/add_question.html', {
        'form': form,
        'dayprogram': dayprogram,
    })

@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, pk=question_id)

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            return redirect('tripapp:dayprogram_questions', dayprogram_id=question.dayprogram.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'tripapp/edit_question.html', {
        'form': form,
        'dayprogram': question.dayprogram,
    })

@login_required
def dayprogram_questions(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)
    questions = dayprogram.question_set.all()
    trip = dayprogram.trip
    try:
        tripper = Tripper.objects.get(name=request.user, trips=trip)
        is_trip_admin = tripper.is_trip_admin
    except Tripper.DoesNotExist:
        is_trip_admin = False
    return render(request, 'tripapp/dayprogram_questions.html', {
        'dayprogram': dayprogram,
        'questions': questions,
        'is_trip_admin': is_trip_admin,
    })

@tripper_required
def add_point(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    if not trip.trippers.filter(name=request.user).exists():
        return HttpResponseForbidden("You are not allowed to add points to this trip.")
    if request.method == 'POST':
        form = PointForm(request.POST)
        if form.is_valid():
            point = form.save(commit=False)
            point.trip = trip
            point.save()
            form.save_m2m()  # Save the many-to-many relationships
            return redirect('tripapp:trip_points', trip_id=trip.id)
    else:
        form = PointForm(trip=trip)
    return render(request, 'tripapp/add_point.html', {
        'form': form,
        'trip': trip,
    })

@tripper_required
def edit_point(request, trip_id, point_id):
    trip = get_object_or_404(Trip, id=trip_id)
    point = get_object_or_404(Point, id=point_id)

    if request.method == 'POST':
        form = PointForm(request.POST, instance=point, trip=trip)
        if form.is_valid():
            form.save()
            return redirect('tripapp:trip_points', trip_id=trip.id)
    else:
        form = PointForm(instance=point, trip=trip)

    return render(request, 'tripapp/edit_point.html', {'form': form, 'trip': trip})

@tripper_required
def delete_point(request, trip_id, point_id):
    if request.method == 'POST':
       trip = get_object_or_404(Trip, id=trip_id)
       point = get_object_or_404(Point, id=point_id)
       point.delete()
       return redirect('tripapp:trip_points', trip_id=trip.id)
    else:
       return redirect('tripapp:trip_points', trip_id=trip.id)


@login_required
def trip_points(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    points = trip.points.all()
    routes = Route.objects.filter(dayprogram__trip=trip)
    return render(request, 'tripapp/trip_points.html', {
        'trip': trip,
        'points': points,
        'routes': routes,
    })

@login_required
def add_bingocard(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    if request.method == 'POST':
        form = BingoCardForm(request.POST, request.FILES)
        if form.is_valid():
            bingocard = form.save(commit=False)
            bingocard.trip = trip
            bingocard.save()
            return redirect('tripapp:tripadmin_bingocards', trip_id=trip.id)
    else:
        form = BingoCardForm()

    return render(request, 'tripapp/add_bingocard.html', {
        'form': form,
        'trip': trip,
    })

@login_required
def tripadmin_bingocards(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    bingocards = trip.bingocards.all()
    user_is_tripper = Tripper.objects.filter(name=request.user, trips=trip).exists()
    return render(request, 'tripapp/tripadmin_bingocards.html', {
        'trip': trip,
        'bingocards': bingocards,
        'user_is_tripper': user_is_tripper,
    })

def permission_denied(request):
    return render(request, 'tripapp/permission_denied.html')

@csrf_exempt
def save_event(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        marker_type = request.POST.get('type') 
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        event_id = request.POST.get('id')
        trip_id = request.POST.get('trip')
        trip = get_object_or_404(Trip, pk=trip_id)
        dayprogram_id = request.POST.get('dayprogram')
        if dayprogram_id:
           dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)

        if event_id:
            # Update existing event
            event = get_object_or_404(Point, pk=event_id)
            event.name = name
            event.marker_type = marker_type
            event.latitude = latitude
            event.longitude = longitude
            event.trip = trip
            event.save()
            if dayprogram_id:
               event.dayprograms.add(dayprogram) 
        else:
            # Create new event
            event = Point.objects.create(
                name=name,
                marker_type=marker_type,
                latitude=latitude,
                longitude=longitude,
                trip = trip
            )
            if dayprogram_id:
               event.dayprograms.add(dayprogram)

        return JsonResponse({'message': 'Event saved successfully!'})

    return JsonResponse({'error': 'Invalid request'})

@login_required
def add_logentry(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    current_user = request.user
    tripper = Tripper.objects.filter(name=current_user.username).first()

    if request.method == 'POST':
        form = LogEntryForm(request.POST)
        if form.is_valid():
            log_entry = form.save(commit=False)
            log_entry.tripper = tripper
            log_entry.save()
            return redirect('tripapp:dayprogram_detail', id=dayprogram.id)
    else:
        form = LogEntryForm(initial={'dayprogram': dayprogram})

    return render(request, 'tripapp/add_logentry.html', {'form': form, 'dayprogram': dayprogram})

@tripper_required
def dayprogram_add(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)

    last_dayprogram = trip.dayprograms.order_by('-dayprogramnumber').first()
    if last_dayprogram:
        next_dayprogramnumber = last_dayprogram.dayprogramnumber + 1
        next_tripdate = last_dayprogram.tripdate + timedelta(days=1)
    else:
        next_dayprogramnumber = 1
        next_tripdate = trip.date_from

    if request.method == 'POST':
        form = DayProgramForm(request.POST)
        if form.is_valid():
            dayprogram = form.save(commit=False)
            dayprogram.trip = trip
            dayprogram.save()

            # Update Trip.date_to
            if trip.date_to is None or dayprogram.tripdate > trip.date_to:
                trip.date_to = dayprogram.tripdate
                trip.save()

            return redirect('tripapp:dayprogram_detail', id=dayprogram.pk)
    else:
        form = DayProgramForm(initial={
            'dayprogramnumber': next_dayprogramnumber,
            'tripdate': next_tripdate
        })

    return render(request, 'tripapp/dayprogram_add.html', {
        'form': form,
        'trip': trip,
    })

@login_required
def tribe_trip_organize(request,tribe_id,trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    tribe = get_object_or_404(Tribe, pk=tribe_id)
    admin_trips = Trip.objects.filter(trippers__name=request.user, trippers__is_trip_admin=True)
    tripper = None
    if request.user.is_authenticated:
        tripper = Tripper.objects.filter(user=request.user).first()

    return render(request, 'tripapp/tribe_trip_organize.html', 
        {'tribe': tribe,
         'trip': trip,
         'admin_trips' : admin_trips,
         'tripper':tripper
        })

@login_required
def add_badge_and_question(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)
    if request.method == 'POST':
        badge_form = BadgeplusQForm(request.POST, request.FILES)
        question_form = QuestionplusBForm(request.POST)
        if badge_form.is_valid() and question_form.is_valid():
            badge = badge_form.save(commit=False)
            badge.achievement_method = 'question_correct'
            badge.tribe = dayprogram.trip.tribe
            badge.save()

            question = question_form.save(commit=False)
            question.dayprogram = dayprogram
            question.badge = badge
            question.save()

            return redirect('tripapp:dayprogram_questions', dayprogram_id=dayprogram.pk)  
    else:
        badge_form = BadgeplusQForm()
        question_form = QuestionplusBForm()

    return render(request, 'tripapp/add_badge_and_question.html', {
        'badge_form': badge_form,
        'question_form': question_form,
        'dayprogram': dayprogram
    })

@login_required
def add_link(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)

    if request.method == 'POST':
        form = LinkForm(request.POST, request.FILES)
        if form.is_valid():
            link = form.save(commit=False)
            link.dayprogram = dayprogram
            link.save()
            return redirect('tripapp:trip_dayprograms', trip_id=dayprogram.trip.id)
    else:
        form = LinkForm(dayprogram=dayprogram)

    return render(request, 'tripapp/add_link.html', {
        'form': form,
        'dayprogram': dayprogram
    })

@login_required
def edit_link(request, dayprogram_id, link_id):
    dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)
    link = get_object_or_404(Link, pk=link_id)

    if request.method == 'POST':
        form = LinkForm(request.POST, instance=link, dayprogram=dayprogram)
        if form.is_valid():
            form.save()
            return redirect('tripapp:dayprogram_links', dayprogram_id=dayprogram.id)
    else:
        form = LinkForm(instance=link, dayprogram=dayprogram)

    return render(request, 'tripapp/edit_link.html', {'form': form, 'link': link})

@login_required
def delete_link(request, dayprogram_id, link_id):
    if request.method == 'POST':
       dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
       link = get_object_or_404(Link, id=link_id)
       link.delete()
       return redirect('tripapp:dayprogram_links', dayprogram_id=dayprogram.id)
    else:
       return redirect('tripapp:dayprogram_links', dayprogram_id=dayprogram.id)



@login_required
def dayprogram_links(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)
    links = dayprogram.links.all()
    trip = dayprogram.trip
    try:
        tripper = Tripper.objects.get(name=request.user, trips=trip)
        is_trip_admin = tripper.is_trip_admin
    except Tripper.DoesNotExist:
        is_trip_admin = False
    return render(request, 'tripapp/dayprogram_links.html', {
        'dayprogram': dayprogram,
        'links': links,
        'is_trip_admin': is_trip_admin,
    })



@login_required
def upload_route(request,trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    if request.method == 'POST':
        form = RouteForm(request.POST, request.FILES)
        if form.is_valid():
            route = form.save()
            dayprogram = route.dayprogram
            trip_id = dayprogram.trip.id

            return redirect('tripapp:trip_points', trip_id=trip_id)
    else:
        form = RouteForm(trip=trip)
    return render(request, 'tripapp/upload_route.html', {'form': form, 'trip':trip})

@login_required
def delete_route(request, trip_id, route_id):
    if request.method == 'POST':
       trip = get_object_or_404(Trip, id=trip_id)
       route = get_object_or_404(Route, id=route_id)
       route.delete()
       return redirect('tripapp:trip_points', trip_id=trip.id)
    else:
       return redirect('tripapp:trip_points', trip_id=trip.id)


@login_required
def add_suggestion(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, pk=dayprogram_id)

    if request.method == 'POST':
        form = SuggestionForm(request.POST)
        if form.is_valid():
            suggestion = form.cleaned_data['suggestion']
            user_suggestion = _("Suggestion by %(username)s: %(suggestion)s") % {
                "username": request.user.username,
                "suggestion": suggestion,
                }
            if dayprogram.possible_activities:
                dayprogram.possible_activities += f"\n{user_suggestion}"
            else:
                dayprogram.possible_activities = user_suggestion
            dayprogram.save()
            return redirect('tripapp:dayprogram_detail',  id=dayprogram.id)
    else:
        form = SuggestionForm()

    context = {
        'form': form,
        'dayprogram': dayprogram,
    }
    return render(request, 'tripapp/add_suggestion.html', context)

@login_required
def add_expense(request, trip_id, tripper_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    tripper = get_object_or_404(Tripper, pk=tripper_id)
    next_url = request.GET.get('next')  
    dayprogram_id = request.GET.get('dayprogram_id') 

    if request.method == 'POST':
        form = TripExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.trip = trip
            expense.tripper = tripper
            expense.save()

            if next_url == 'balance':
                return redirect('tripapp:trip_balance', trip_id=trip.id)
            elif next_url == 'dayprogram_detail' and dayprogram_id:
                return redirect('tripapp:dayprogram_detail', id=dayprogram_id)
    else:
        last_expense = TripExpense.objects.filter(tripper=tripper).order_by('-date').first()
        last_currency = last_expense.currency if last_expense else settings.APP_CURRENCY
        form = TripExpenseForm(initial={'currency': last_currency})
    return render(request, 'tripapp/add_expense.html', {'form': form, 'trip': trip, 'tripper':tripper})

@tripper_required
def trip_balance(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    balance = trip.calculate_balance()
    all_zero = all(balance_value == 0 for balance_value in balance.values())

    abs_balance = {tripper: {'balance': balance_value, 'abs_balance': abs(balance_value)} for tripper, balance_value in balance.items()}
    app_currency = settings.APP_CURRENCY
    return render(request, 'tripapp/trip_balance.html', {'trip': trip, 'balance': abs_balance, 'app_currency':app_currency, 'all_zero':all_zero})

@tripper_required
def trip_expenses_list(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    expenses = trip.expenses.all().order_by('date')
    tripper = Tripper.objects.filter(name=request.user.username).first()
    app_currency = settings.APP_CURRENCY
    filter_date = request.GET.get('filter_date')
    filter_category = request.GET.get('filter_category')

    if filter_date:
        expenses = expenses.filter(date=filter_date)
    if filter_category:
        expenses = expenses.filter(category=filter_category)

    total_amount = sum(expense.converted_amount for expense in expenses)

    return render(request, 'tripapp/trip_expenses_list.html', {'trip': trip, 'expenses': expenses, 'tripper':tripper, 'app_currency':app_currency, 'total_amount': total_amount})

@login_required
def trip_update(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if request.method == 'POST':
        form = TripUpdateForm(request.POST, request.FILES, instance=trip)
        if form.is_valid():
            form.save()
            return redirect('tripapp:tribe_trip_organize', tribe_id=trip.tribe.id, trip_id=trip.id)  
    else:
        form = TripUpdateForm(instance=trip)

    return render(request, 'tripapp/trip_update.html', {'form': form, 'trip': trip})

 
def set_timezone(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_timezone = data.get("timezone")
        if user_timezone:
            timezone.activate(user_timezone)
            request.session['user_timezone'] = user_timezone  
            return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            new_password = form.cleaned_data.get('new_password')
            if new_password:
                user.password = make_password(new_password)
            user.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('tripapp:trip_list')  
        else:
            messages.error(request, "There was an error updating your profile.")
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'tripapp/update_profile.html', {'form': form})

@login_required
def trip_checklist(request,slug):
    trip = get_object_or_404(Trip, slug=slug)
    checklist = Checklist.objects.get_or_create(trip=trip)[0]
    checklist_items = ChecklistItem.objects.filter(checklist=checklist).order_by('is_completed', 'id')  # Sorteer op is_completed en vervolgens op id
    items = checklist.items.all()
    tripper = None
    if request.user.is_authenticated:
        tripper = Tripper.objects.filter(user=request.user).first()

    return render(request, 'tripapp/trip_checklist.html', {
        'trip': trip,
        'checklist': checklist,
        'items': checklist_items,
        'tripper': tripper
    })

@login_required
def task_manager(request):
    tasks = [
        {"name": "assign_badges", "description": "Assign badges to trippers."},
        {"name": "fetch_locations_for_tripper", "description": "Fetch locations for trippers."},
        {"name": "fetch_and_store_immich_photos", "description": "Fetch and store Immich photos."},
        {"name": "update_dayprogram_maps", "description": "Add staticmaps per day for offline use."},
        {"name": "fetch_and_store_yesterdays_weather", "description": "Get weatherreports to show in offline zip"},
       ]

    for task in tasks:
        last_task = Task.objects.filter(func=f"tripapp.tasks.{task['name']}").order_by("-started").first()
        task["last_run"] = last_task.started if last_task else "Never"
        task["status"] = last_task.success if last_task else "Not Run"
        task["last_message"] = last_task.result if last_task else "No Message"

    previous_url = request.META.get('HTTP_REFERER', '/fallback-url/')

    if request.method == "POST":
        task_name = request.POST.get("task_name")

        async_task(f"tripapp.tasks.{task_name}")

        return redirect("tripapp:task_manager")

    return render(request, "tripapp/task_manager.html", {"tasks": tasks, "previous_url":previous_url})

@login_required
def trip_documents_view(request, trip_id):
    trip = get_object_or_404(Trip.objects.prefetch_related('dayprograms__links'), id=trip_id)
    trip_documents = Link.objects.filter(dayprogram__trip=trip).order_by('dayprogram__tripdate')
    tripper_documents = TripperDocument.objects.filter(tripper__trips=trip)

    filter_date = request.GET.get('filter_date')
    filter_category = request.GET.get('filter_category')

    if filter_date:
        trip_documents = trip_documents.filter(dayprogram__tripdate=filter_date)

    if filter_category:
        trip_documents = trip_documents.filter(category=filter_category)
        tripper_documents = tripper_documents.filter(category=filter_category)

    return render(request, 'tripapp/trip_documents.html', {
        'trip': trip,
        'trip_documents': trip_documents,
        'tripper_documents': tripper_documents,
    })

@login_required
def add_or_edit_scheduled_item(request, dayprogram_id, scheduled_item_id=None):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
 
    if scheduled_item_id:
        scheduled_item = get_object_or_404(ScheduledItem, id=scheduled_item_id, dayprogram=dayprogram)
    else:
        scheduled_item = None

    if request.method == 'POST':
        form = ScheduledItemForm(request.POST, instance=scheduled_item)
        if form.is_valid():
            scheduled_item = form.save(commit=False)
            scheduled_item.dayprogram = dayprogram
            scheduled_item.save()
            return redirect('tripapp:dayprogram_detail', id=dayprogram.id)
    else:
        form = ScheduledItemForm(instance=scheduled_item)

    return render(request, 'tripapp/scheduled_item_form.html', {'form': form, 'dayprogram': dayprogram, 'scheduled_item': scheduled_item})


@login_required
def dayprogram_scheduled_items(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    scheduled_items = dayprogram.scheduled_items.all().order_by('start_time')

    return render(request, 'tripapp/dayprogram_scheduled_items.html', 
         {'dayprogram': dayprogram, 
          'scheduled_items' : scheduled_items,
         })

@login_required
def delete_scheduled_item(request, dayprogram_id, scheduled_item_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    scheduled_item = get_object_or_404(ScheduledItem, id=scheduled_item_id, dayprogram=dayprogram)

    if request.method == 'POST':
        scheduled_item.delete()
        return redirect('tripapp:dayprogram_scheduled_items', dayprogram_id=dayprogram.id)

    return render(request, 'tripapp/confirm_delete_scheduled_item.html', 
        {'scheduled_item': scheduled_item, 'dayprogram': dayprogram})


@login_required
def upload_tripper_document(request):
    tripper = request.user.tripper
    if request.method == 'POST':
        form = TripperDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.tripper = tripper
            document.save()
            return redirect('tripapp:tripper_profile', tripper_id=tripper.id)
    return redirect('tripapp:tripper_profile', tripper_id=tripper.id)

@login_required
def delete_tripper_document(request, document_id):
    tripper = request.user.tripper
    document = get_object_or_404(TripperDocument, id=document_id)
    if document.tripper != request.user.tripper:
        return HttpResponseForbidden("You do not have permission to delete this document.")
    document.delete()
    return redirect('tripapp:tripper_profile', tripper_id=tripper.id)



def export_trip_markdown_zip(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    
    # Markdown-content
    md_content = f"# {trip.name}\n\n**Datum:** {trip.date_from} - {trip.date_to}\n\n{trip.description}\n\n## Programma\n"
    
    image_files = []  

    for day in trip.dayprograms.all().order_by('dayprogramnumber'):
        md_content += f"\n### {day.tripdate}: {day.description}\n{day.necessary_info}\n{day.possible_activities}\n"

        for image in day.images.all():
            image_filename = os.path.basename(image.image.name)  
            md_content += f"\n![{image.description}]({image_filename})\n"
            image_files.append((image_filename, image.image.path))  


    md_content += "\n## Trippers\n"
    for tripper in trip.trippers.all():
        md_content += f"- {tripper.name}\n"
        if tripper.photo:
            photo_filename = os.path.basename(tripper.photo.name)
            md_content += f"  ![{tripper.name}]({photo_filename})\n"
            image_files.append((photo_filename, tripper.photo.path))

    md_content += "\n## Bingocards\n"
    bingocards = trip.bingocards.all()
    if not bingocards:
        md_content += "_Not on this trip._\n"

    # ZIP
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr(f"{trip.slug}.md", md_content)  
        
        for filename, filepath in image_files:
            if os.path.exists(filepath):  
                zip_file.write(filepath, filename)

    zip_buffer.seek(0)  
    
    # ZIP as download
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{trip.slug}.zip"'
    return response



def encode_image_to_base64(image_path, max_size=(300, 300)):  
    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
    
    if not os.path.exists(full_path):
        print(f"⚠️ file not found: {full_path}")  
        return None

    try:
        with PILImage.open(full_path) as img:
            img.thumbnail(max_size)  
            buffer = BytesIO()
            img.save(buffer, format="PNG") 
            base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{base64_str}"    
    except Exception as e:
        print(f"⚠️ Error processing image: {e}")
        return None

def generate_html_with_images(trip):

    html_content = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{trip.name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            img {{ max-width: 100%; height: auto; margin-top: 10px; }}
            .container {{ max-width: 800px; margin: auto; }}
            .card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{trip.name}</h1>
            <p>{trip.description}</p>

    """
    if trip.image:
        img_base64 = encode_image_to_base64(trip.image.name,(800,600))  

        if img_base64:
            html_content += f'<img src="{img_base64}" >'


    html_content += "<h2>📅 Dayprograms</h2>"

    for day in trip.dayprograms.all().order_by('dayprogramnumber'):

        html_content += f"""
        <div class="card">
            <h3>🗓 {day.dayprogramnumber} - {day.tripdate} - {day.description}</h3>
            <p>{day.necessary_info}</p>
            <p>{day.possible_activities}</p>"""
        
        if day.recorded_weather_text:
            html_content += f"""<p>{day.recorded_weather_text}</p>"""


        if day.scheduled_items.exists():
            html_content += "<h4> Scheduled Items</h4><ul>"
            for item in day.scheduled_items.all():
                html_content += f"""
                <li>
                    <strong>{item.start_time} - {item.end_time}:</strong> {item.category}  
                    <br>📍 {item.start_address} ➝ {item.end_address if item.end_address else 'N/A'}
                </li>
                """
                if item.category == "Transportation" and item.transportation_type:
                    html_content += f"<br>🚗 Type: {item.transportation_type}"
            html_content += "</ul>"


        for image in day.images.all():
            img_base64 = encode_image_to_base64(image.image.name)  
            angle = random.randint(-3, 3)

            if img_base64:
                html_content += f"""
                <div style="display:inline-block; background:#fff; padding:10px 10px 30px 10px;
                            margin:10px; box-shadow:2px 2px 8px rgba(0,0,0,0.3);
                            border:1px solid #ccc; transform:rotate({angle}deg);">
                <img src="{img_base64}" style="max-width:200px; display:block; margin:0 auto;">
                </div>
                """
            else:
                html_content += "<p>⚠️ No Image File</p>"

        if day.logentries.exists():
            html_content += "<h4>📝 Log Entries</h4>"
            for log in day.logentries.all():
                likes_str = ""
                if log.likes.exists():
                    likes_list = [f"{like.tripper.name} {like.emoji}" for like in log.likes.select_related("tripper")]
                    likes_str = " [" + ", ".join(likes_list) + "]"
                html_content += f"<p><strong>{log.tripper.name}:</strong> {log.logentry_text}{likes_str}</p>"

        if day.map_image:
            img_base64 = encode_image_to_base64(day.map_image.name)  
            html_content += f'<p><img src="{img_base64}" ></p>'

        if day.question_set.exists():
            html_content += "<h4>❓ Question(s)</h4><ul>"
            for question in day.question_set.all():
                html_content += f"<strong>{question.question_text}</strong><br>"
                if trip.date_to > timezone.now().date():
                    html_content += f"not yet disclosed"
                else:
                    html_content += f"Answer we were looking for: {question.correct_answer}"
            html_content += "</ul>"

        html_content += f"""</div>"""


    html_content += "<h2>Trippers</h2>"

    for tripper in trip.trippers.all():
        html_content += f"""
            <div class="card">
            <h3>{tripper.name}</h3>"""

        # Badges
        badge_assignments = BadgeAssignment.objects.filter(trip=trip, tripper=tripper).select_related('badge')
        badge_count = badge_assignments.count()
        html_content += f'<p>🏅 Badges this trip: {badge_count}</p>'

        for assignment in badge_assignments:
            if assignment.badge.image:
                img_base64 = encode_image_to_base64(assignment.badge.image.name)
                if img_base64:
                    html_content += f'<img src="{img_base64}" width="200px"  height="200px">'
            

        html_content += "</div>"


    #bingocards            
    html_content += "<h2>TripBingo</h2>"
    trippers_on_this_trip = trip.trippers.annotate(
        answer_count=Count('bingoanswer', filter=Q(bingoanswer__bingocard__trip=trip))
    ).order_by('-answer_count')
    html_content += f""" <div class="card">"""
    html_content += f"""<table>"""
    for tripper in trippers_on_this_trip:
        html_content += f"""
        <tr>
            <td>{ tripper.name }</td>
            <td style="text-align:right;">{ tripper.answer_count }</td>
        </tr>"""
    html_content += f"""</table>"""
    html_content += "</div><br />"
    bingocards = trip.bingocards.all()
    for bingocard in bingocards:
        html_content += f""" <div class="card">"""
        html_content += "<table border='0' style='width:100%; border-collapse:collapse;'>"
        html_content += f'''
        <tr>
        <td style="vertical-align: top; padding: 8px;">
            <p style="font-variant-caps: all-small-caps;font-weight: bold;">{bingocard.description}</p>
        </td>
        </tr>
        <tr>
        <td style="vertical-align: top; padding: 8px;">
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;">
        '''

        bingo_answers = BingoAnswer.objects.filter(bingocard=bingocard).select_related('tripper')
        
        if bingo_answers.exists():
            for answer in bingo_answers:
                if answer.answerimage:
                    img_base64 = encode_image_to_base64(answer.answerimage.name)
                    if img_base64:
                        html_content += f'''
                        <div style="text-align: center; border: 1px solid #ccc; padding: 6px; border-radius: 8px;">
                        <strong>{answer.tripper.name}</strong><br>
                        <img src="{img_base64}" style="max-width:200px; max-height:200px;">
                        </div>
                        '''
        else:
            html_content += "No Answers"

        html_content += "</div></td></tr></table>"

        html_content += "</div>"

    html_content += """
        </div>
    </body>
    </html>
    """

    return html_content


def create_zip_with_html(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)    
    zip_filename = f"{trip.slug}_export.zip"
    zip_path = os.path.join(settings.MEDIA_ROOT, "exports", zip_filename) 
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)  

    html_content = generate_html_with_images(trip)
    html_filename = f"{trip.slug}_trip_export.html"

    with zipfile.ZipFile(zip_path, "w") as zip_file:
        zip_file.writestr(html_filename, html_content)
    
    return FileResponse(open(zip_path, "rb"), as_attachment=True, filename=zip_filename)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import timedelta
from .models import Trip, DayProgram
from django.contrib.auth.decorators import login_required

@csrf_exempt
@login_required
def reorder_dayprograms(request, trip_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        trip = Trip.objects.get(id=trip_id)
    except Trip.DoesNotExist:
        return JsonResponse({'error': 'Trip not found'}, status=404)

    tripper = request.user.tripper
    if not tripper or not tripper.is_trip_admin or trip not in tripper.trips.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        order = data['order']

        programs = {dp.id: dp for dp in DayProgram.objects.filter(trip=trip)}

        current_date = trip.date_from

        for item in sorted(order, key=lambda x: x['new_order']):
            dp_id = int(item['id'])
            if dp_id in programs:
                dp = programs[dp_id]
                dp.dayprogramnumber = item['new_order']
                dp.tripdate = current_date
                dp.save()
                current_date += timedelta(days=1)

        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


from rest_framework import generics
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.response import Response
from rest_framework.views import APIView

class TripViewSet(viewsets.ModelViewSet):
    permission_classes = [HasAPIKey]
    queryset = Trip.objects.all().order_by('-date_from')
    serializer_class = TripSerializer


class TripsByTribeView(generics.ListAPIView):
    permission_classes = [HasAPIKey]
    serializer_class = TripSerializer

    def get_queryset(self):
        tribe_id = self.kwargs['tribe_id']
        return Trip.objects.filter(tribe__id=tribe_id).order_by('-date_from')

class TripsByTripperView(generics.ListAPIView):
    permission_classes = [HasAPIKey]
    serializer_class = TripSerializer

    def get_queryset(self):
        tripper_id = self.kwargs['tripper_id']
        return Trip.objects.filter(trippers__id=tripper_id).order_by('-date_from')


class TribeMapDataAPIView(APIView):
    permission_classes = [HasAPIKey]

    def get(self, request, tribe_id):
        tribe = get_object_or_404(Tribe, id=tribe_id)
        trips = Trip.objects.filter(tribe=tribe)

        data = []
        for trip in trips:
            code = trip.get_first_country_code()
            coords = get_country_coords(code or 'nl')
            if coords:
                photo_url = trip.image.url if trip.image else static('favicon/apple-touch-icon.png')
                data.append({
                    'name': trip.name,
                    'latitude': coords[0],
                    'longitude': coords[1],
                    'photo_url': request.build_absolute_uri(photo_url),
                    'trip_url': request.build_absolute_uri(reverse('tripapp:trip_detail', kwargs={'slug': trip.slug})),
                })

        serializer = TripMapDataSerializer(data, many=True)
        return Response(serializer.data)



class LogEntryViewSet(viewsets.ModelViewSet):
    queryset = LogEntry.objects.all()

    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        logentry = self.get_object()
        tripper = Tripper.objects.get(user=request.user)
        emoji = request.data.get('emoji')

        if not tripper or not emoji:
            return Response(
                {"error": _("Tripper and emoji mandatory.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        like, created = LogEntryLike.objects.get_or_create(
            logentry=logentry,
            tripper=tripper,
            emoji=emoji,
        )
        if not created:
            return Response(
                {"detail": _("You already liked this log with this emoji.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = LogEntryLikeSerializer(like)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='unlike')
    def unlike(self, request, pk=None):
        logentry = self.get_object()
        tripper_id = request.data.get('tripper')
        emoji = request.data.get('emoji')

        if not tripper_id or not emoji:
            return Response(
                {"error": _("Tripper and emoji mandatory.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        like = LogEntryLike.objects.filter(
            logentry=logentry,
            tripper_id=tripper_id,
            emoji=emoji
        ).first()

        if not like:
            return Response(
                {"detail": _("There is no like with this emoji that can be removed.")},
                status=status.HTTP_404_NOT_FOUND
            )

        like.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



@login_required
def badge_creator(request):
    return render(request, "tripapp/badge_creator.html")

@login_required
def save_badge(request):
    if request.method == "POST":
        data_url = request.POST.get("badge_image")
        badge_name = request.POST.get("badge_name")

        if not badge_name or not data_url:
            return JsonResponse({"status": "error", "message": "Naam en afbeelding zijn verplicht"}, status=400)

        format, imgstr = data_url.split(";base64,")
        ext = format.split("/")[-1]
        badge = Badge(user=request.user, name=badge_name)
        badge.image.save(f"{badge_name}.{ext}", ContentFile(base64.b64decode(imgstr)))
        badge.save()
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"}, status=400)

####tripoutline

class TripOutlineCreateView(generics.CreateAPIView):
    queryset = TripOutline.objects.all()
    serializer_class = TripOutlineSerializer

@login_required
def create_itineraryidea_overnightlocations(request):
    return render(request, 'tripapp/create_tripoutline.html')

@login_required
def create_itineraryidea_daylocations(request):
    return render(request, 'tripapp/create_itineraryidea_daylocations.html')


@csrf_exempt
def save_tripoutline(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body)

            idea = ItineraryIdea.objects.create(
                name=payload.get("name") or f"Itinerary {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                created_by=request.user,
            )

            items_data = payload.get("items", [])
            day_counter = 1
            days_saved = 0

            for item in items_data:
                nights = int(item.get("nights", 1))  # default 1 night
                description = item.get("description", "")

                for n in range(nights):
                    day = ItineraryIdeaDay.objects.create(
                        itineraryidea=idea,
                        day_sequence=day_counter,
                        day_description=description,
                        day_possible_date=None,  
                    )

                    OvernightLocation.objects.create(
                        day=day,
                        latitude=item.get("latitude"),
                        longitude=item.get("longitude"),
                        radius=item.get("radius", 100),
                        description=description,
                    )

                    day_counter += 1
                    days_saved += 1

            return JsonResponse({
                "status": "ok",
                "itinerary_id": idea.id,
                "days_saved": days_saved,
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def save_tripoutline_daylocations(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name") or f"Itinerary {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            idea = ItineraryIdea.objects.create(
                name=name,
                created_by=request.user,
            )

            items_data = json.loads(request.POST.get("items_json", "[]"))

            day_counter = 1
            for item in items_data:
                description = item.get("description", "")
                day = ItineraryIdeaDay.objects.create(
                    itineraryidea=idea,
                    day_sequence=day_counter,
                    day_description=description,
                )

                DayLocation.objects.create(
                    day=day,
                    sequence=item.get("sequence"),
                    latitude=item.get("latitude"),
                    longitude=item.get("longitude"),
                    radius=item.get("radius", 100),
                    description=description,
                )

                day_counter += 1

            return redirect('tripapp:itinerary_daylocations_dragdrop', pk=idea.id)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


def tripoutline_list(request):
    outlines = TripOutline.objects.prefetch_related("items").all().order_by("-created_at")
    return render(request, "tripapp/tripoutline_list.html", {"outlines": outlines})



from .forms import TripOutlineForm, TripOutlineItemFormSet

def tripoutline_detail(request, pk):
    outline = get_object_or_404(TripOutline, pk=pk)

    if request.method == "POST":
        form = TripOutlineForm(request.POST, instance=outline)
        formset = TripOutlineItemFormSet(request.POST, instance=outline)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("tripapp:tripoutline-list")
    else:
        form = TripOutlineForm(instance=outline)
        formset = TripOutlineItemFormSet(instance=outline)

    return render(request, "tripapp/tripoutline_detail.html", {
        "form": form,
        "formset": formset,
        "outline": outline
    })

from django.views.decorators.http import require_POST

@require_POST
def tripoutline_delete(request, pk):
    outline = get_object_or_404(TripOutline, pk=pk)
    outline.delete()
    return redirect("tripapp:tripoutline-list")

@csrf_exempt
def update_tripoutline(request, pk):
    outline = get_object_or_404(TripOutline, pk=pk)

    if request.method == "POST":
        try:
            payload = json.loads(request.body)

            outline.name = payload.get("name") or outline.name
            outline.save()

            outline.items.all().delete()
            for item in payload.get("items", []):
                TripOutlineItem.objects.create(
                    outline=outline,
                    sequence=item.get("sequence"),
                    description=item.get("description"),
                    overnightlocation=item.get("overnightlocation"),
                    latitude=item.get("latitude"),
                    longitude=item.get("longitude"),
                    radius=item.get("radius", 0),
                )

            return JsonResponse({"status": "ok", "outline_id": outline.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return render(request, "tripapp/update_tripoutline.html", {
        "outline": outline,
        "items_json": json.dumps([
            {
                "id": item.id,
                "sequence": item.sequence,
                "latitude": float(item.latitude),
                "longitude": float(item.longitude),
                "radius": item.radius,
                "description": item.description or "",
                "overnightlocation": item.overnightlocation or "",
            }
            for item in outline.items.all().order_by("sequence")
        ]),
    })

### itinerary ideas

from .models import ItineraryIdea, ItineraryIdeaDay, DayLocation, OvernightLocation

@login_required
def pastecreate_itineraryidea(request):
    return render(request, "tripapp/import_itinerary.html")


def import_itineraryidea(request):
    import_status = None

    if request.method == "POST":
        json_input = request.POST.get("json_input")
        if not json_input:
            import_status = "No JSON provided"
        else:
            try:
                data = json.loads(json_input)

                user = request.user if request.user.is_authenticated else None
                if not user:
                    import_status = "You must be logged in or provide a user_id in JSON"
                    return render(request, "tripapp/import_itinerary.html", {"import_status": import_status})

                # create itinerary
                itinerary = ItineraryIdea.objects.create(
                    name=data.get("name", f"Itinerary {timezone.now().strftime('%Y-%m-%d %H:%M')}"),
                    created_by=user
                )

                for day_data in data.get("days", []):
                    day = ItineraryIdeaDay.objects.create(
                        itineraryidea=itinerary,
                        day_sequence=day_data.get("day_sequence"),
                        day_description=day_data.get("day_description", ""),
                        day_possible_date=day_data.get("day_possible_date")
                    )

                    for loc in day_data.get("day_locations", []):
                        DayLocation.objects.create(
                            day=day,
                            sequence=loc.get("sequence"),
                            latitude=loc.get("lat"),
                            longitude=loc.get("long"),
                            radius=loc.get("radius", 100),
                            description=loc.get("description", "")
                        )

                    overnight_data = day_data.get("overnightlocation")
                    if overnight_data:
                        OvernightLocation.objects.create(
                            day=day,
                            latitude=overnight_data.get("lat"),
                            longitude=overnight_data.get("long"),
                            radius=overnight_data.get("radius", 100),
                            description=overnight_data.get("description", "")
                        )

                import_status = f"Success! Itinerary '{itinerary.name}' imported with {len(data.get('days', []))} days."
                return redirect("tripapp:itineraryidea-list")

            except json.JSONDecodeError:
                import_status = "Invalid JSON"
            except Exception as e:
                import_status = f"Error: {str(e)}"

    return render(request, "tripapp/import_itinerary.html", {"import_status": import_status})



def itineraryidea_list(request):
    itineraryideas = ItineraryIdea.objects.prefetch_related("itineraryidea_days").all().order_by("-created_at")
    return render(request, "tripapp/itineraryidea_list.html", {"itineraryideas": itineraryideas})


# show an itineraryidea on a map in order to have it edited
def itineraryidea_edit(request, pk):
    idea = get_object_or_404(ItineraryIdea, pk=pk)

    days = []
    for day in idea.itineraryidea_days.all().order_by("day_sequence"):
        day_locations = list(day.day_locations.all().order_by("sequence"))
        overnight = getattr(day, 'overnightlocation', None)

        days.append({
            'day_id': day.id,
            'day_sequence': day.day_sequence,
            'day_description': day.day_description,
            'day_locations': day_locations,
            'overnightlocation': overnight,
        })

    return render(request, 'tripapp/itineraryidea_update.html', {
        'idea': idea,
        'days': days
    })

# update the itineraryidea after user has edited on a map
@login_required
def update_itineraryidea(request, pk):
    print("User:", request.user, "authenticated:", request.user.is_authenticated)
    idea = get_object_or_404(ItineraryIdea, pk=pk)

    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            items = payload.get("items", [])

            # Update name
            idea.name = payload.get("name", idea.name)
            idea.updated_by = request.user
            idea.save()

            # remove existing
            for day in idea.itineraryidea_days.all():
                day.day_locations.all().delete()
                if hasattr(day, "overnightlocation"):
                    day.overnightlocation.delete()
            idea.itineraryidea_days.all().delete()

            # create new
            day_counter = 1
            for item in items:
                is_overnight = item.get("overnight", False)
                day_sequence = item.get("day_sequence", day_counter)
                description = item.get("description", "")

                day = ItineraryIdeaDay.objects.create(
                    itineraryidea=idea,
                    day_sequence=day_sequence,
                    day_description=description
                )

                if is_overnight:
                    OvernightLocation.objects.create(
                        day=day,
                        latitude=item["latitude"],
                        longitude=item["longitude"],
                        radius=item.get("radius", 100),
                        description=description
                    )
                else:
                    DayLocation.objects.create(
                        day=day,
                        sequence=item.get("sequence", 1),
                        latitude=item["latitude"],
                        longitude=item["longitude"],
                        radius=item.get("radius", 100),
                        description=description
                    )

                day_counter += 1

            return JsonResponse({"status": "ok", "itinerary_id": idea.id})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
@require_POST
def itineraryidea_delete(request, pk):
    idea = get_object_or_404(ItineraryIdea, pk=pk)
    idea.delete()
    return redirect("tripapp:itineraryidea-list")


from tripapp.schemas import ITINERARY_JSON_SCHEMA

def itinerary_schema_view(request):
    schema_json = json.dumps(ITINERARY_JSON_SCHEMA, indent=2)
    return render(request, "tripapp/itinerary_schema.html", {"schema": schema_json})



from .forms import CreateTripFromItineraryForm
from .utils import create_trip_from_itinerary

@login_required
def itineraryidea_to_trip(request, pk):
    itinerary = get_object_or_404(ItineraryIdea, pk=pk)

    if request.method == "POST":
        form = CreateTripFromItineraryForm(request.POST, user=request.user)
        if form.is_valid():
            tribe = form.cleaned_data["tribe"]
            start_date = form.cleaned_data["start_date"]

            trip = create_trip_from_itinerary(itinerary, tribe, start_date, user=request.user)

            return redirect("tripapp:trip_list")
    else:
        form = CreateTripFromItineraryForm(user=request.user)

    return render(request, "tripapp/itineraryidea_to_trip.html", {
        "form": form,
        "itinerary": itinerary,
    })


@login_required
def itinerary_daylocations_dragdrop(request, pk):
    itinerary = get_object_or_404(ItineraryIdea, id=pk)
    all_daylocations = DayLocation.objects.filter(day__itineraryidea=itinerary)
    unassigned_daylocations = all_daylocations.filter(day__isnull=True)
    itinerary_days = ItineraryIdeaDay.objects.filter(itineraryidea=itinerary).prefetch_related('day_locations')

    context = {
        'itinerary_idea': itinerary,
        'unassigned_daylocations': unassigned_daylocations,
        'itinerary_days': itinerary_days,
    }

    return render(request, 'tripapp/itinerary_dragdrop.html', context)

@csrf_exempt
def save_daylocation_assignments(request):
    data = json.loads(request.body)
    assignments = data.get("assignments", [])

    for a in assignments:
        loc_id = a.get("location_id")
        day_id = a.get("day_id")
        seq = a.get("sequence")
        try:
            loc = DayLocation.objects.get(id=loc_id)
            loc.day_id = day_id
            loc.sequence = seq if seq else None
            loc.save()
        except DayLocation.DoesNotExist:
            continue

    return JsonResponse({"status": "ok"})

