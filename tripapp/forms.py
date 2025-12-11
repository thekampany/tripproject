from django import forms
from .models import Badge
from .models import BadgeAssignment
from .models import Trip
from .models import ChecklistItem
from .models import Image
from .models import BingoAnswer
from .models import DayProgram
from .models import Tripper
from .models import Tribe
from .models import Question
from .models import Point
from .models import BingoCard
from .models import LogEntry
from .models import Link
from .models import Route
from .models import TripExpense
from .models import TripBudget
from .models import ScheduledItem
from .models import TripperDocument
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.core.validators import MaxLengthValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class TripperForm(forms.ModelForm):
    class Meta:
        model = Tripper
        fields = ['photo', 'dawarich_url', 'dawarich_api_key', 'immich_url', 'immich_api_key','currency']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dawarich_url'].initial = 'https://your-dawarich-url.com/api/v1/points'
        self.fields['immich_url'].initial = 'https://your-immich-server.com' 
        if not self.instance.pk or not self.instance.currency:
            self.fields['currency'].initial = settings.APP_CURRENCY        

class TripperAdminForm(forms.ModelForm):
    class Meta:
        model = Tripper
        fields = ['is_trip_admin']


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['image']

    day_program = forms.ModelChoiceField(queryset=DayProgram.objects.all(), widget=forms.HiddenInput())


class BadgeForm(forms.ModelForm):
   ACHIEVEMENT_METHOD_CHOICES = [
        ('time_based', 'Time Based'),
        ('question_correct', 'Correct Answer to Question'),
        ('admin_assigned', 'Admin Assigned')
   ]

   achievement_method = forms.ChoiceField(
        choices=ACHIEVEMENT_METHOD_CHOICES,
        required=True
   )

   class Meta:
        model = Badge
        fields = ['name', 'image', 'achievement_method','assignment_date', 'tribe' ]
        widgets = {
           'assignment_date': forms.DateInput(attrs={'type':'date'}),
        }
   def clean(self):
        cleaned_data = super().clean()
        assignment_date = cleaned_data.get('assignment_date')
        achievement_method = cleaned_data.get('achievement_method')

        if achievement_method == 'time_based' and not assignment_date:
            self.add_error('assignment_date', 'Assignment date is required for time-based achievements.')
        if achievement_method == 'admin_assigned' and assignment_date:
            self.add_error('assignment_date', 'Assignment date should not be set for admin-assigned achievements.')
        if achievement_method == 'question_correct' and assignment_date:
            self.add_error('assignment_date', 'Assignment date should not be set for question-correct achievements.')
        return cleaned_data


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['tribe', 'name', 'description', 'date_from', 'date_to', 'image', 'country_codes', 'use_expenses' ]
        widgets = {
            'date_from': forms.DateInput(attrs={'type': 'date'}),
            'date_to': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        tribe = kwargs.pop('tribe', None)  
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        if user:
            self.fields['tribe'].queryset = user.userprofile.tribes.all()
        if tribe:
            self.initial['tribe'] = tribe
   

class AddTrippersForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Select Trippers'
    )
    def __init__(self, *args, **kwargs):
        tribe = kwargs.pop('tribe', None)
        trip = kwargs.pop('trip', None)
        super().__init__(*args, **kwargs)
        if tribe:
            self.fields['users'].queryset = User.objects.filter(userprofile__tribes=tribe).distinct()
            self.fields['users'].label = f'Select Trippers (Tribe: {tribe.name})'
        if trip:
            initial_trippers = trip.trippers.values_list('name', flat=True)
            initial_users = User.objects.filter(username__in=initial_trippers)
            self.initial['users'] = initial_users

class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = ['text', 'is_completed']

class AnswerForm(forms.Form):
    answer = forms.CharField(
        max_length=255,
        label="",  
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Your answer here...')  
            }
        )
    )

class AnswerImageForm(forms.Form):
    answerimage = forms.ImageField()

class BingoCardForm(forms.ModelForm):
    class Meta:
        model = BingoCard
        fields = ['description', 'bingoimage', 'answerimage']

class BingoAnswerForm(forms.ModelForm):
    class Meta:
        model = BingoAnswer
        fields = ['answerimage']


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class TribeCreationForm(forms.ModelForm):
    class Meta:
        model = Tribe
        fields = ['name']


class DayProgramForm(forms.ModelForm):
    overnight_point = forms.ModelChoiceField(
        queryset=Point.objects.none(),
        required=False,
        label='Choose optional overnight location',
        help_text='Select existing location (type "bed")',
    )

    class Meta:
        model = DayProgram
        fields = ['description', 'tripdate', 'dayprogramnumber', 'necessary_info',
                  'possible_activities', 'overnight_point', 'overnight_location']
        widgets = {
            'tripdate': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.TextInput(attrs={'maxlength': 50}),
            'overnight_location': forms.TextInput(attrs={'placeholder': 'Or enter text'}),
        }

    def __init__(self, *args, **kwargs):
        trip = kwargs.pop('trip', None)
        super().__init__(*args, **kwargs)
        self.fields['description'].validators.append(MaxLengthValidator(50))

        if trip:
            self.fields['overnight_point'].queryset = Point.objects.filter(trip=trip, marker_type='bed')

        if self.instance.pk:
            related_points = self.instance.points.filter(marker_type='bed')
            if related_points.exists():
                self.fields['overnight_point'].initial = related_points.first()

    def clean(self):
        cleaned_data = super().clean()
        point = cleaned_data.get('overnight_point')
        location = cleaned_data.get('overnight_location')

        if point and not location:
            cleaned_data['overnight_location'] = point.name
        return cleaned_data

 
    
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'correct_answer', 'badge']
    def __init__(self, *args, **kwargs):
        dayprogram = kwargs.pop('dayprogram', None)
        super().__init__(*args, **kwargs)
        if dayprogram:
            tribe = dayprogram.trip.tribe
            self.fields['badge'].queryset = Badge.objects.filter(
                models.Q(level='global') |
                models.Q(level='tribal', tribe=tribe)
            )

class PointForm(forms.ModelForm):
    MARKER_TYPE_CHOICES = [
        ('default', 'Default'),
        ('bed', 'Bed'),
        ('restaurant', 'Restaurant')
    ]

    marker_type = forms.ChoiceField(
        choices=MARKER_TYPE_CHOICES,
        required=False
    )
    class Meta:
        model = Point
        fields = ['name', 'latitude', 'longitude', 'dayprograms','marker_type']
        widgets = {
            'dayprograms': forms.CheckboxSelectMultiple()
        }
    def __init__(self, *args, **kwargs):
        trip = kwargs.pop('trip', None)
        super(PointForm, self).__init__(*args, **kwargs)
        if trip:
            self.fields['dayprograms'].queryset = DayProgram.objects.filter(trip=trip).order_by('tripdate')


class BadgeAssignmentForm(forms.ModelForm):
    class Meta:
        model = BadgeAssignment
        fields = ['badge']

    def __init__(self, *args, trip=None, tripper=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Badge.objects.filter(level='tribal')
        # trip level filtering kan nog niet want bestaat nog niet in model
        if trip:
            qs = qs.filter(tribe=trip.tribe)

        if tripper and trip:
            already = BadgeAssignment.objects.filter(tripper=tripper, trip=trip).values_list('badge_id', flat=True)
            if self.instance and self.instance.pk:
                current_id = self.instance.badge_id
                already = [b for b in already if b != current_id]
            qs = qs.exclude(id__in=already)

        self.fields['badge'].queryset = qs

class BaseBadgeAssignmentFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop('trip', None)
        self.tripper = kwargs.pop('tripper', None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['trip'] = self.trip
        kwargs['tripper'] = self.tripper
        return super()._construct_form(i, **kwargs)


from django.forms import inlineformset_factory

BadgeAssignmentFormSet = inlineformset_factory(
    Tripper,
    BadgeAssignment,
    form=BadgeAssignmentForm,
    formset=BaseBadgeAssignmentFormSet,
    extra=1,
    can_delete=True
)

class LogEntryForm(forms.ModelForm):
    class Meta:
        model = LogEntry
        fields = ['dayprogram', 'logentry_text']
        widgets = {
            'dayprogram': forms.HiddenInput()
        }


class BadgeplusQForm(forms.ModelForm):
    class Meta:
        model = Badge
        fields = ['name', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['achievement_method'] = forms.CharField(widget=forms.HiddenInput(), initial='question_correct')
        self.fields['level'] = forms.CharField(widget=forms.HiddenInput(), initial='tribal')

class QuestionplusBForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'correct_answer']

class LinkForm(forms.ModelForm):
    scheduled_item = forms.ModelChoiceField(
        queryset=ScheduledItem.objects.all(),
        required=False,  
        empty_label="Choose Scheduled Item for this link/document (optional)",  
        widget=forms.Select(attrs={'class': 'form-control'})  
    )
    class Meta:
        model = Link
        fields = ['url', 'document','description', 'category', 'scheduled_item']
    def __init__(self, *args, **kwargs):
        dayprogram = kwargs.pop('dayprogram', None)
        super().__init__(*args, **kwargs)

        if dayprogram:
            self.fields['scheduled_item'].queryset = ScheduledItem.objects.filter(dayprogram=dayprogram)



class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['dayprogram', 'description', 'gpx_file']
    def __init__(self, *args, **kwargs):
        trip = kwargs.pop('trip', None)
        super(RouteForm, self).__init__(*args, **kwargs)
        if trip:
            self.fields['dayprogram'].queryset = DayProgram.objects.filter(trip=trip)

class SuggestionForm(forms.Form):
    suggestion = forms.CharField(widget=forms.Textarea, label='')

class TripExpenseForm(forms.ModelForm):
    class Meta:
        model = TripExpense
        fields = ['description', 'amount', 'currency', 'date', 'receipt', 'category']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if 'currency' not in initial:
            initial['currency'] = settings.APP_CURRENCY
        kwargs['initial'] = initial

        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_currency(self):
        currency = self.cleaned_data.get('currency')
        if currency:
            return currency.upper()
        return currency

class TripUpdateForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['name', 'description', 'image', 'country_codes', 'use_expenses']



class UserUpdateForm(forms.ModelForm):
    new_password = forms.CharField(
        label="New Password", 
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter new password'}), 
        required=False
    )
    confirm_password = forms.CharField(
        label="Confirm Password", 
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password'}), 
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and new_password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned_data


class ScheduledItemForm(forms.ModelForm):
    class Meta:
        model = ScheduledItem
        fields = [
            'category',
            'transportation_type',
            'start_time',
            'end_time',
            'start_address',
            'end_address',
        ]
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'start_address': forms.TextInput(attrs={'class': 'form-control'}),
            'end_address': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'transportation_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

class TripperDocumentForm(forms.ModelForm):
    class Meta:
        model = TripperDocument
        fields = ['document', 'description', 'category']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'documentdescription...'}),
        }


from .models import TripOutline, TripOutlineItem

class TripOutlineForm(forms.ModelForm):
    class Meta:
        model = TripOutline
        fields = ["name"]

class TripOutlineItemForm(forms.ModelForm):
    class Meta:
        model = TripOutlineItem
        fields = ["sequence", "description", "overnightlocation", "latitude", "longitude", "radius"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sequence"].required = False
        self.fields["radius"].required = False
        # Default values
        if self.instance.pk is None:  
            self.fields["sequence"].initial = 1
            self.fields["radius"].initial = 100
            self.fields["latitude"].initial = 0
            self.fields["longitude"].initial = 0

TripOutlineItemFormSet = inlineformset_factory(
    TripOutline,
    TripOutlineItem,
    form=TripOutlineItemForm,
    fields=["sequence", "description", "overnightlocation", "latitude", "longitude", "radius"],
    extra=0,
    can_delete=True
)



class CreateTripFromItineraryForm(forms.Form):
    tribe = forms.ModelChoiceField(queryset=Tribe.objects.none())
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["tribe"].queryset = Tribe.objects.filter(members__user=user)



class TripBudgetForm(forms.ModelForm):
    class Meta:
        model = TripBudget
        fields = ['category', 'amount',  'currency']