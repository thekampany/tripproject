from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User 
from django.conf import settings
import uuid

# Create your models here.

class Tribe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tribes = models.ManyToManyField(Tribe, related_name='members')

    def __str__(self):
        return self.user.username

class Badge(models.Model):
    ACHIEVEMENT_METHODS = [
        ('admin_assigned', 'Assigned by Admin'),
        ('question_correct', 'Correct Answer to Question'),
        ('time_based' , 'Assigned on a specific date'),
    ]
    LEVEL = [
        ('global', 'Global'),
        ('tribal', 'Tribal'),
    ]

    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='badges/')
    achievement_method = models.CharField(max_length=20, choices=ACHIEVEMENT_METHODS, default='admin_assigned')
    level = models.CharField(max_length=20,choices=LEVEL, default='tribal')
    assignment_date = models.DateField(null=True, blank=True)
    tribe = models.ForeignKey(Tribe, on_delete=models.CASCADE, null=True, blank=True, related_name='badges')

    def __str__(self):
        return self.name

class Trip(models.Model):
    tribe = models.ForeignKey(Tribe, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='trip_images/', blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    date_from = models.DateField(blank=True, null=True)
    date_to = models.DateField(blank=True, null=True)
    country_codes = models.CharField(max_length=200, blank=True, null=True, help_text="Comma-separated list of country codes")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_country_codes(self):
        return self.country_codes.split(",") if self.country_codes else []

class DayProgram(models.Model):
    trip = models.ForeignKey(Trip, related_name='dayprograms', on_delete=models.CASCADE)
    description = models.TextField()
    tripdate = models.DateField('date')
    dayprogramnumber = models.IntegerField()
    possible_activities = models.TextField(blank=True)
    necessary_info = models.TextField(blank=True)

    def __str__(self):
        return f"{self.trip.name} - {self.description[:50]}"

class Image(models.Model):
    day_program = models.ForeignKey(DayProgram, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='day_program_images/')
    description = models.CharField(max_length=255, blank=True)


class Tripper(models.Model):
    name = models.CharField(max_length=100)
    trips = models.ManyToManyField(Trip, related_name='trippers')
    badges = models.ManyToManyField(Badge, related_name='trippers', blank=True)
    photo = models.ImageField(upload_to='tripper_photos/', null=True, blank=True)
    is_trip_admin = models.BooleanField(default=False)

    def count_badges(self):
        return self.badges.count()

    def __str__(self):
        return self.name

class Checklist(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='checklist')

    def __str__(self):
        return f"Checklist for {self.trip.name}"

class ChecklistItem(models.Model):
    checklist = models.ForeignKey(Checklist, related_name='items', on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class Question(models.Model):
    dayprogram = models.ForeignKey(DayProgram, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=255)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)

    def __str__(self):
        return f"Question for {self.dayprogram.tripdate}"

class Point(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='points')
    dayprograms = models.ManyToManyField(DayProgram, blank=True, related_name='points')

    def __str__(self):
        return self.name

class BingoCard(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bingocards')
    description = models.TextField()
    bingoimage = models.ImageField(upload_to='bingocards/', blank=True, null=True)
    answerimage = models.ImageField(upload_to='answers/', blank=True, null=True)

    def __str__(self):
        return f'BingoCard for {self.trip.name} - {self.description[:20]}'

class BingoAnswer(models.Model):
    tripper = models.ForeignKey(Tripper, on_delete=models.CASCADE)
    bingocard = models.ForeignKey(BingoCard, on_delete=models.CASCADE)
    answerimage = models.ImageField(upload_to='bingoanswers/')

    def __str__(self):
        return f"{self.tripper.name} - {self.bingocard.description}"


class BadgeAssignment(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='badge_assignments', null=True, blank=True)
    tripper = models.ForeignKey(Tripper, on_delete=models.CASCADE, related_name='badge_assignments')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='badge_assignments')
    date_assigned = models.DateField(auto_now_add=True)

    def __str__(self):
        if self.trip:
            return f'{self.badge.name} assigned to {self.tripper.name} during {self.trip.name}'
        else:
            return f'{self.badge.name} assigned to {self.tripper.name}'



class LogEntry(models.Model):
    dayprogram = models.ForeignKey(DayProgram, related_name='logentries', on_delete=models.CASCADE)
    tripper = models.ForeignKey(Tripper, related_name='logentries', on_delete=models.CASCADE)
    logentry_text = models.TextField()

    def __str__(self):
        return f"{self.tripper.name} - {self.logentry_text[:50]}"

