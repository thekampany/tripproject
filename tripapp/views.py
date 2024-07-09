
# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from .models import Trip, Tripper, Badge, DayProgram, Checklist, ChecklistItem, Image, Question, Point
from .models import BingoCard, BingoAnswer, BadgeAssignment
from .models import Tribe, UserProfile
from .forms import BadgeForm, TripForm, ChecklistItemForm, ImageForm, BingoAnswerForm
from .forms import CustomUserCreationForm
from .forms import AnswerForm, AnswerImageForm, TripperForm, TripperAdminForm
from .forms import TribeCreationForm, AddTrippersForm, DayProgramForm
from .forms import QuestionForm, PointForm, BingoCardForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
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
from datetime import timedelta
import uuid
from .decorators import tripper_required

def index(request):
    category = "roadtrip"
    background_image_url = get_random_unsplash_image(category)
    return render(request, 'tripapp/index.html', {'background_image_url': background_image_url})


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

    return render(request, 'tripapp/tribe_trips.html', 
        {'tribes': tribes,
         'trips': trips, 
         'background_image_url': background_image_url,
         'admin_trips': admin_trips
        })


@login_required
def invite_to_tribe(request):
    if request.method == 'POST':
        email = request.POST['email']
        tribe_id = request.POST['tribe_id']
        tribe = get_object_or_404(Tribe, id=tribe_id)
        current_site = get_current_site(request)
        subject = 'Invitation to join a tribe'

        html_content = render_to_string('tripapp/invite_email.html', {
            'user': request.user,
            'tribe_id': tribe_id,
            'tribe_name': tribe.name,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(tribe_id)),
            'protocol': 'https' if request.is_secure() else 'http'
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
    for trip in trips:
        trip.country_codes_list = trip.country_codes.split(',') if trip.country_codes else []
    return render(request, 'tripapp/trip_list.html', {'tribes': tribes, 'trips': trips, 'background_image_url': background_image_url})

@login_required
def trip_detail(request, slug):
    trip = get_object_or_404(Trip, slug=slug)
    dayprograms = DayProgram.objects.filter(trip=trip).order_by('tripdate')
    checklist = Checklist.objects.get_or_create(trip=trip)[0]
    checklist_items = ChecklistItem.objects.filter(checklist=checklist).order_by('is_completed', 'id')  # Sorteer op is_completed en vervolgens op id
    items = checklist.items.all()
    return render(request, 'tripapp/trip_detail.html', {
        'trip': trip,
        'dayprograms': dayprograms,
        'checklist': checklist,
        'items': checklist_items
    })

@login_required
def create_trip(request):
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
        form = TripForm(user=request.user)
    return render(request, 'tripapp/create_trip.html', {'form': form})

@login_required
def trip_trippers(request, id):
    trip = get_object_or_404(Trip, pk=id)
    #trippers = trip.trippers.all()
    #trippers = trip.trippers.annotate(badge_count=Count('badge_assignments')).order_by('-badge_count')
    trippers = trip.trippers.annotate(
        badge_count=Count('badge_assignments', filter=Q(badge_assignments__trip=trip))
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
        form = BadgeForm()
        form.fields['tribe'].queryset = tribes

    return render(request, 'tripapp/upload_badge.html', {'form': form})






@login_required
def tripper_badges(request, tripper_id):
    tripper = get_object_or_404(Tripper, id=tripper_id)
    badges = tripper.badges.all()
    return render(request, 'tripapp/tripper_badges.html', {'tripper': tripper, 'badges': badges})

@login_required
def trip_tripper_badges(request, trip_id, tripper_id):
    trip = get_object_or_404(Trip, id=trip_id)
    tripper = get_object_or_404(Tripper, id=tripper_id)
    badges = tripper.badges.all()
    return render(request, 'tripapp/trip_tripper_badges.html', {'trip': trip, 'tripper': tripper, 'badges': badges})

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
    images = dayprogram.images.all()
    trippers_on_this_trip = dayprogram.trip.trippers.all()
    trippers_names = [tripper.name for tripper in trippers_on_this_trip]
    return render(request, 'tripapp/dayprogram_detail.html', 
         {'dayprogram': dayprogram, 
          'images': images, 
          'questions': questions,
          'form': form,
          'today': timezone.now().date(),
          'trippers_names': trippers_names
         })


@login_required
def add_image(request, dayprogram_id):
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    if request.method == 'POST':
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.dayprogram = dayprogram
            form.save()
            return redirect('tripapp:dayprogram_detail', id=dayprogram_id)
    else:
        form = ImageForm(initial={'dayprogram': dayprogram})
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
def check_answer(request, pk):
    dayprogram = get_object_or_404(DayProgram, pk=pk)
    question = get_object_or_404(Question, dayprogram=dayprogram)

    if question is None:
        return redirect('tripapp:dayprogram_detail', pk=dayprogram.pk)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.cleaned_data['answer']
            if answer.lower() in question.correct_answer.lower():
                # Badge toekennen
                current_user = request.user
                tripper = Tripper.objects.filter(name=current_user.username).first()
                #tripper = get_object_or_404(Tripper, user=request.username)
                tripper.badges.add(question.badge)
                return redirect('tripapp:badge_claimed', badge_id=question.badge.id)
            else:
                return redirect('tripapp:dayprogram_detail', pk=dayprogram.pk)

    return redirect('tripapp:dayprogram_detail', pk=dayprogram.pk)

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
    points = trip.points.all()
    return render(request, 'tripapp/trip_map.html', {'trip': trip, 'points': points})

@login_required
def trip_dayprogram_points(request, trip_id, dayprogram_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    dayprogram = get_object_or_404(DayProgram, id=dayprogram_id)
    trip_points = Point.objects.filter(trip=trip)

    points = trip_points.filter(dayprograms=dayprogram)

    context = {
        'trip': trip,
        'dayprogram': dayprogram,
        'points': points,
    }

    return render(request, 'tripapp/trip_dayprogram_points.html', context) 

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

    if request.method == 'POST':
        form = BingoAnswerForm(request.POST, request.FILES)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.tripper = tripper
            answer.bingocard = bingocard
            answer.save()
            #return redirect('tripapp:bingocard_detail', pk=bingocard.id)
            return redirect('tripapp:trip_bingocards',trip_id=bingocard.trip.id) 
    else:
        form = BingoAnswerForm()

    return render(request, 'tripapp/upload_answerimage.html', {'form': form, 'bingocard': bingocard})

@login_required
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
            if created:
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
            for user in users:
                tripper, created = Tripper.objects.get_or_create(name=user)
                tripper.trips.add(trip)
            for user in users.exclude(name__in=trippers):
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
def edit_tripper(request, tripper_id):
    tripper = get_object_or_404(Tripper, id=tripper_id)
    if request.method == 'POST':
        form = TripperAdminForm(request.POST, request.FILES, instance=tripper)
        if form.is_valid():
            form.save()
            return redirect('tripapp:tribe_trips')
    else:
        form = TripperAdminForm(instance=tripper)
    return render(request, 'tripapp/edit_tripper.html', {'form': form, 'tripper': tripper})


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
    return render(request, 'tripapp/trip_dayprograms.html', {
        'trip': trip,
        'dayprograms': dayprograms,
        'user_is_tripper': user_is_tripper,
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
    # Controleer of de huidige gebruiker een tripper is van de trip
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


@login_required
def trip_points(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)
    points = trip.points.all()
    return render(request, 'tripapp/trip_points.html', {
        'trip': trip,
        'points': points,
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
            return redirect('tripapp:trip_bingocards', trip_id=trip.id)
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
