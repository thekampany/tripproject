

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from .models import Trip, Tripper, Badge, DayProgram, Checklist, ChecklistItem, Image, Question, Point
from .models import BingoCard, BingoAnswer, BadgeAssignment
from .models import Tribe, UserProfile, LogEntry, Link, Route, TripExpense, Location, ImmichPhotos
from .forms import BadgeForm, TripForm, ChecklistItemForm, ImageForm, BingoAnswerForm
from .forms import CustomUserCreationForm
from .forms import AnswerForm, AnswerImageForm, TripperForm, TripperAdminForm
from .forms import TribeCreationForm, AddTrippersForm, DayProgramForm
from .forms import QuestionForm, PointForm, BingoCardForm
from .forms import BadgeAssignmentFormSet, LogEntryForm
from .forms import BadgeplusQForm, QuestionplusBForm
from .forms import LinkForm, RouteForm, SuggestionForm, TripExpenseForm, TripUpdateForm, UserUpdateForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .utils import get_random_unsplash_image
from django.db.models import Count, Q
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
#from weasyprint import HTML

from django.utils.timezone import now
from django_q.tasks import async_task
from django_q.models import Task


def index(request):
    category = "roadtrip"
    background_image_url = get_random_unsplash_image(category)
    return render(request, 'tripapp/index.html', {'background_image_url': background_image_url, 'APP_NAME': settings.APP_NAME, 'VERSION':settings.VERSION})


@login_required
def tribe_trips(request):
    user = request.user
    user_profile = request.user.userprofile
    tribes = user_profile.tribes.all()
    trips = Trip.objects.filter(tribe__in=tribes).order_by('-date_from', '-id')
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
        email = request.POST['email']
        tribe_id = request.POST['tribe_id']
        tribe = get_object_or_404(Tribe, id=tribe_id)
        current_site = request.get_host()
        current_port = request.get_port() 
        invite_url = request.build_absolute_uri(f'/register/invite/{urlsafe_base64_encode(force_bytes(tribe_id))}/')
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

        email = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
        email.attach_alternative(html_content, "text/html")
        email.send()

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
    tripper = None
    if request.user.is_authenticated:
        tripper = Tripper.objects.filter(user=request.user).first()
    for trip in trips:
        trip.country_codes_list = trip.country_codes.split(',') if trip.country_codes else []
    return render(request, 'tripapp/trip_list.html', {'tribes': tribes, 'trips': trips, 'background_image_url': background_image_url, 'tripper':tripper})

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

    return render(request, 'tripapp/trip_detail.html', {
        'trip': trip,
        'dayprograms': dayprograms,
        'checklist': checklist,
        'items': checklist_items,
        'today': today,
        'tripper': tripper
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
            tripper, created = Tripper.objects.get_or_create(name=user.username)
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
    ).order_by('-badge_count')

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


#@login_required
#def tripper_badges(request, tripper_id):
#    tripper = get_object_or_404(Tripper, id=tripper_id)
#    badges = tripper.badges.all()
#    return render(request, 'tripapp/tripper_badges.html', {'tripper': tripper, 'badges': badges})

@login_required
def tripper_badgeassignments(request, tripper_id):
    tripper = get_object_or_404(Tripper, id=tripper_id)
    badge_assignments = BadgeAssignment.objects.filter(tripper=tripper).select_related('badge')
    badges = [assignment.badge for assignment in badge_assignments]
    count_tripper_badges = BadgeAssignment.objects.filter(tripper=tripper).count()
    return render(request, 'tripapp/tripper_badgeassignments.html', {'tripper': tripper, 'badges': badges, 'count_tripper_badges':count_tripper_badges})

#@login_required
#def trip_tripper_badges(request, trip_id, tripper_id):
#    trip = get_object_or_404(Trip, id=trip_id)
#    tripper = get_object_or_404(Tripper, id=tripper_id)
#    badges = tripper.badges.all()
#    return render(request, 'tripapp/trip_tripper_badges.html', {'trip': trip, 'tripper': tripper, 'badges': badges})

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
          'previous_dayprogram' : previous_dayprogram,
          'next_dayprogram' : next_dayprogram,
          'logged_on_tripper' : logged_on_tripper
         })


@login_required
def add_image(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    if request.method == 'POST':
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.day_program = dayprogram
            image.save()
            return redirect('tripapp:dayprogram_detail', id=dayprogram_id)
        else:
            print(form.errors)
    else:
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

                return redirect('tripapp:badge_claimed', badge_id=question.badge.id)
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



@login_required
def map_view(request):
    points = Point.objects.all()
    return render(request, 'tripapp/map.html', {'points': points})

@login_required
def trip_map_view(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    points = trip.points.prefetch_related('dayprograms')
    #all visited locations dawarich -- within dates of the trip
    start_of_day = timezone.make_aware(datetime.combine(trip.date_from, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(trip.date_to, datetime.max.time()))
    trippers = trip.trippers.all()
    locations = Location.objects.filter(
        tripper__in=trippers,
        timestamp__range=(start_of_day, end_of_day)
    )
    photolocations = ImmichPhotos.objects.filter(tripper__in=trippers,timestamp__range=(start_of_day, end_of_day))

    return render(request, 'tripapp/trip_map.html', {'trip': trip, 'points': points, 'locations': locations, 'photolocations':photolocations})

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
    locations = Location.objects.filter(tripper__in=trippers,timestamp__range=(start_of_day, end_of_day))
    photolocations = ImmichPhotos.objects.filter(tripper__in=trippers,timestamp__range=(start_of_day, end_of_day))

    trip_name_no_spaces = trip.name.replace(" ", "")
    tribe_name_no_spaces = trip.tribe.name.replace(" ","")
    first_point = points.first() if points.exists() else None

    context = {
        'trip': trip,
        'dayprogram': dayprogram,
        'points': points,
        'trip_name_no_spaces':trip_name_no_spaces,
        'tribe_name_no_spaces' : tribe_name_no_spaces,
        'first_point': first_point,
        'locations': locations,
        'photolocations': photolocations,
    }

    return render(request, 'tripapp/trip_dayprogram_points.html', context) 

@tripper_required
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

    if request.method == 'POST':
        form = BingoAnswerForm(request.POST, request.FILES)
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

            return redirect('tripapp:trip_bingocards',trip_id=bingocard.trip.id) 
    else:
        form = BingoAnswerForm()

    return render(request, 'tripapp/upload_answerimage.html', {'form': form, 'bingocard': bingocard})

@user_owns_tripper
def tripper_profile(request, tripper_id):
    tripper = get_object_or_404(Tripper, id=tripper_id)
    if request.method == 'POST':
        form = TripperForm(request.POST, request.FILES, instance=tripper)
        if form.is_valid():
            form.save()
            return redirect('tripapp:tripper_profile', tripper_id=tripper.id)
    else:
        form = TripperForm(instance=tripper)
    return render(request, 'tripapp/tripper_profile.html', {'form': form, 'tripper': tripper})

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
        formset = BadgeAssignmentFormSet(request.POST, instance=tripper, queryset=BadgeAssignment.objects.filter(trip=trip))
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
        formset = BadgeAssignmentFormSet(instance=tripper, queryset=BadgeAssignment.objects.filter(trip=trip))

    return render(request, 'tripapp/edit_tripper.html', {'form': form, 'formset': formset, 'tripper': tripper, 'trip': trip})



@login_required
def tripper_list(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    trippers = trip.trippers.all()
    return render(request, 'tripapp/tripper_list.html', {'trip': trip, 'trippers': trippers})



@login_required
def edit_dayprogram(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    if request.method == 'POST':
        form = DayProgramForm(request.POST, instance=dayprogram)
        if form.is_valid():
            form.save()
            return redirect('tripapp:trip_dayprograms', trip_id=dayprogram.trip.id)
    else:
        form = DayProgramForm(instance=dayprogram)
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
        form = QuestionForm()

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

def facilmap(request):
    return render(request, 'tripapp/facilmap.html')

def planner_map(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    trip_name_no_spaces = trip.name.replace(" ", "")
    tribe_name_no_spaces = trip.tribe.name.replace(" ","")

    context = {
      'trip' : trip,
      'trip_name_no_spaces' : trip_name_no_spaces,
      'tribe_name_no_spaces' : tribe_name_no_spaces
    }
    if trip.use_facilmap:
       return render(request, 'tripapp/planner_map.html', context )
    else:
       points = trip.points.prefetch_related('dayprograms')
       return render(request, 'tripapp/trip_map.html', {'trip': trip, 'points': points})


@csrf_exempt
def save_event(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        event_id = request.POST.get('id')
        trip_id = request.POST.get('trip')
        trip = get_object_or_404(Trip, pk=trip_id)

        if event_id:
            # Update existing event
            event = get_object_or_404(Point, pk=event_id)
            event.name = name
            event.latitude = latitude
            event.longitude = longitude
            event.trip = trip
            event.save()
        else:
            # Create new event
            event = Point.objects.create(
                name=name,
                latitude=latitude,
                longitude=longitude,
                trip = trip
            )

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
        form = LinkForm()

    return render(request, 'tripapp/add_link.html', {
        'form': form,
        'dayprogram': dayprogram
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
            user_suggestion = f"Suggestion by {request.user.username}: {suggestion}"
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
    abs_balance = {tripper: {'balance': balance_value, 'abs_balance': abs(balance_value)} for tripper, balance_value in balance.items()}
    app_currency = settings.APP_CURRENCY
    return render(request, 'tripapp/trip_balance.html', {'trip': trip, 'balance': abs_balance, 'app_currency':app_currency})

@tripper_required
def trip_expenses_list(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    expenses = trip.expenses.all().order_by('date')
    tripper = Tripper.objects.filter(name=request.user.username).first()
    app_currency = settings.APP_CURRENCY
    return render(request, 'tripapp/trip_expenses_list.html', {'trip': trip, 'expenses': expenses, 'tripper':tripper, 'app_currency':app_currency})

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

#def generate_pdf(request, trip_id):
#    trip = get_object_or_404(Trip, id=trip_id)  
#    dayprograms = DayProgram.objects.filter(trip=trip).order_by('tripdate').prefetch_related('images')

    #checklist = Checklist.objects.get_or_create(trip=trip)[0]
    #checklist_items = ChecklistItem.objects.filter(checklist=checklist).order_by('is_completed', 'id') 
    #items = checklist.items.all()
    #bingo

#     trip = get_object_or_404(Trip, pk=trip_id)
#     expenses = trip.expenses.all().order_by('date')
#     tripper = Tripper.objects.filter(name=request.user.username).first()
#     app_currency = settings.APP_CURRENCY
#     html_string = render_to_string('tripapp/trip_pdf.html', {'trip': trip,'expenses':expenses,'tripper':tripper,'app_currency':app_currency})
#     pdf = HTML(string=html_string).write_pdf()
#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = 'inline; filename="trip_report.pdf"'
#     return response
 
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
    ]

    for task in tasks:
        last_task = Task.objects.filter(func=f"tripapp.tasks.{task['name']}").order_by("-started").first()
        task["last_run"] = last_task.started if last_task else "Never"
        task["status"] = last_task.success if last_task else "Not Run"
        task["last_message"] = last_task.result if last_task else "No Message"

    if request.method == "POST":
        task_name = request.POST.get("task_name")

        async_task(f"tripapp.tasks.{task_name}")

        return redirect("tripapp:task_manager")

    return render(request, "tripapp/task_manager.html", {"tasks": tasks})

@login_required
def trip_documents_view(request, trip_id):
    trip = get_object_or_404(Trip.objects.prefetch_related('dayprograms__links'), id=trip_id)
    trip_documents = []

    for dayprogram in trip.dayprograms.all():
        trip_documents.extend(dayprogram.links.all())

    return render(request, 'tripapp/trip_documents.html', {'trip': trip, 'trip_documents': trip_documents})
