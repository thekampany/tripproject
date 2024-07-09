from django import forms
from .models import Badge
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
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

class TripperForm(forms.ModelForm):
    class Meta:
        model = Tripper
        fields = ['photo']

class TripperAdminForm(forms.ModelForm):
    class Meta:
        model = Tripper
        fields = ['badges', 'is_trip_admin']


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['day_program', 'image', 'description']

    day_program = forms.ModelChoiceField(queryset=DayProgram.objects.all(), widget=forms.HiddenInput())


class BadgeForm(forms.ModelForm):
   class Meta:
        model = Badge
        fields = ['name', 'image', 'assignment_date', 'tribe' ]

   def clean(self):
        cleaned_data = super().clean()
        assignment_date = cleaned_data.get('assignment_date')

        if assignment_date:
            cleaned_data['achievement_method'] = 'time_based'
        else:
            cleaned_data['achievement_method'] = 'admin_assigned'
        return cleaned_data

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['tribe', 'name', 'description', 'date_from', 'date_to', 'image' ]
        widgets = {
            'date_from': forms.DateInput(attrs={'type': 'date'}),
            'date_to': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['tribe'].queryset = user.userprofile.tribes.all()


#User = get_user_model()

#class AddTrippersForm(forms.Form):
#    users = forms.ModelMultipleChoiceField(
#        queryset=User.objects.none(),
#        widget=forms.CheckboxSelectMultiple,
#        required=True
#    )
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
        if trip:
            initial_trippers = trip.trippers.values_list('name', flat=True)
            initial_users = User.objects.filter(username__in=initial_trippers)
            self.initial['users'] = initial_users

class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = ['text', 'is_completed']

class AnswerForm(forms.Form):
    answer = forms.CharField(label='Your Answer', max_length=255)

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
    class Meta:
        model = DayProgram
        fields = ['description', 'tripdate', 'dayprogramnumber', 'possible_activities', 'necessary_info']
        widgets = {
            'tripdate': forms.DateInput(attrs={'type': 'date'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'correct_answer', 'badge']


class PointForm(forms.ModelForm):
    class Meta:
        model = Point
        fields = ['name', 'latitude', 'longitude', 'dayprograms']
        widgets = {
            'dayprograms': forms.CheckboxSelectMultiple()
        }
    def __init__(self, *args, **kwargs):
        trip = kwargs.pop('trip', None)
        super(PointForm, self).__init__(*args, **kwargs)
        if trip:
            self.fields['dayprograms'].queryset = DayProgram.objects.filter(trip=trip)
