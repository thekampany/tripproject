from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User 
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
import uuid
import requests
from decimal import Decimal
from django.conf import settings 
from PIL import Image as PilImage, ImageOps

from io import BytesIO
from django.core.files.base import ContentFile

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
        ('admin_assigned', 'Assigned by your TourAdmin'),
        ('question_correct', 'Correct Answer to Question'),
        ('time_based' , 'Assigned on a specific date'),
        ('threshold' , 'Assigned when you did something multiple times'),
    ]
    LEVEL = [
        ('global', 'Global'),
        ('tribal', 'Tribal'),
        ('trip', 'Trip')
    ]
    THRESHOLD_TYPES = [
        ('bingo_answer_uploads', 'Bingo Answer Uploads'),
        ('correct_answers', 'Correct Answers'),
        ('image_uploads', 'Image Uploads'),
        ('tripper_has_api_key','User has api integrations configured'),
        ('log_entries','Log Entries'),
        ('trip_count','Trip Count'),
        ('log_likes', 'Log Likes')
    ]

    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='badges/')
    achievement_method = models.CharField(max_length=20, choices=ACHIEVEMENT_METHODS, default='admin_assigned')
    level = models.CharField(max_length=20,choices=LEVEL, default='tribal')
    assignment_date = models.DateField(null=True, blank=True)
    tribe = models.ForeignKey(Tribe, on_delete=models.CASCADE, null=True, blank=True, related_name='badges')
    #trip
    threshold_value = models.PositiveIntegerField(null=True, blank=True, help_text="The value that needs to be reached to earn this badge.")
    threshold_type = models.CharField(max_length=20, choices=THRESHOLD_TYPES, null=True, blank=True, help_text="The type of threshold to achieve.")

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
    country_codes = models.CharField(max_length=200, blank=True, null=True, help_text="A two-letter country code of the country you are visiting. Separate by comma in case of multiple countries")
    use_facilmap = models.BooleanField(default=False)
    use_expenses = models.BooleanField(default=False, help_text="Off means that we choose not to look at who owes who how much")

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.name}-{self.tribe.name}")
            new_slug = base_slug
            counter = 1

            while Trip.objects.filter(slug=new_slug).exists():
                new_slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = new_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_country_codes(self):
        return self.country_codes.split(",") if self.country_codes else []

    def get_first_country_code(self):
        country_codes = self.get_country_codes()
        return country_codes[0] if country_codes else None

    def calculate_balance(self):
        trippers = self.trippers.all() 
        expenses = self.expenses.all() 
        
        total_expenses = sum(expense.converted_amount for expense in expenses)
        num_trippers = trippers.count()
        equal_share = total_expenses / Decimal(num_trippers) if num_trippers > 0 else 0

        balance = {}
        for tripper in trippers:
            tripper_expenses = expenses.filter(tripper=tripper)
            spent = sum(expense.converted_amount for expense in tripper_expenses)
            balance[tripper.name] = spent - equal_share

        return balance



    def has_expenses(self):
        return self.expenses.exists() 

class DayProgram(models.Model):
    trip = models.ForeignKey(Trip, related_name='dayprograms', on_delete=models.CASCADE)
    description = models.TextField()
    tripdate = models.DateField('date')
    dayprogramnumber = models.IntegerField()
    possible_activities = models.TextField(blank=True)
    necessary_info = models.TextField(blank=True)
    map_image = models.ImageField(upload_to='maps/', blank=True, null=True)  
    recorded_weather = models.JSONField(null=True, blank=True)
    recorded_weather_text = models.TextField(null=True, blank=True)
    overnight_location = models.CharField(max_length=255, blank=True, null=True, help_text="Spend the night in (eg. camping, hotelname, city)")

    def __str__(self):
        return f"{self.trip.name} - {self.dayprogramnumber} - {self.description[:50]}"

class Image(models.Model):
    day_program = models.ForeignKey(DayProgram, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='day_program_images/')
    description = models.CharField(max_length=255, blank=True)
    #uploaded_by

    def save(self, *args, **kwargs):
        img = PilImage.open(self.image)
        img = ImageOps.exif_transpose(img)
        max_size = (600, 600)  
        img.thumbnail(max_size)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=75)
        buffer.seek(0)
        self.image.save(self.image.name, ContentFile(buffer.read()), save=False)
        super().save(*args, **kwargs)


class Tripper(models.Model):
    name = models.CharField(max_length=100)
    trips = models.ManyToManyField(Trip, related_name='trippers')
    badges = models.ManyToManyField(Badge, related_name='trippers', blank=True)
    photo = models.ImageField(upload_to='tripper_photos/', null=True, blank=True)
    is_trip_admin = models.BooleanField(default=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    dawarich_url = models.URLField(help_text="Enter dawarich-url including api/v/points if you use Dawarich and want to see locations where you have been displayed on the map", null=True, blank=True)  
    dawarich_api_key = models.CharField(max_length=100,help_text="dawarich-api-key", null=True, blank=True)  
    immich_url = models.URLField(help_text="Enter immich-url in order to see locations where you took a picture plotted on the trip map", null=True, blank=True) 
    immich_api_key = models.CharField(max_length=100, help_text="immich-api-key", null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    #def count_badges(self):
    #    return self.badges.count()

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
    MARKER_TYPE = [
        ('default', 'Default'),
        ('bed', 'Bed'),
        ('restaurant', 'Restaurant')
    ]
    marker_type = models.CharField(max_length=20, choices=MARKER_TYPE, default='default')

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

    def save(self, *args, **kwargs):
        if self.answerimage and hasattr(self.answerimage, "file"):
            img = PilImage.open(self.answerimage)
            img = ImageOps.exif_transpose(img)
            max_size = (600, 600)  
            img.thumbnail(max_size)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=75)
            buffer.seek(0)

            self.answerimage.save(
                self.answerimage.name,
                ContentFile(buffer.read()),
                save=False
            )

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.tripper.name} - {self.bingocard.description}"

    def count_trip_answers(self):
        return BingoAnswer.objects.filter(
            tripper=self.tripper,
            bingocard__trip=self.bingocard.trip
        ).count()

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

    def like_count(self):
        return self.likes.count()


class LogEntryLike(models.Model):
    logentry = models.ForeignKey(
        LogEntry,
        related_name='likes',
        on_delete=models.CASCADE
    )
    tripper = models.ForeignKey(
        Tripper,
        related_name='logentry_likes',
        on_delete=models.CASCADE
    )
    emoji = models.CharField(max_length=10)  
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('logentry', 'tripper', 'emoji')

    def __str__(self):
        return f"{self.tripper.name} liked {self.logentry.id} with {self.emoji}"

class Link(models.Model):
    CATEGORY_CHOICES = [
        ('', 'No Category'),
        ('Transportation', 'Transportation'),
        ('Lodging', 'Lodging'),
        ('Food and Drinks','Food and Drinks'),
        ('Activity', 'Activity'),
        ('Other', 'Other'),
    ]
    dayprogram = models.ForeignKey(DayProgram, related_name='links', on_delete=models.CASCADE)
    url = models.URLField(blank=True, null=True)
    document = models.FileField(upload_to='documents/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True,
        default=''
    )
    scheduled_item = models.ForeignKey(
        'ScheduledItem',
        on_delete=models.SET_NULL,
        related_name='links',
        null=True,
        blank=True,
        help_text="Optional: Associate this link with a specific ScheduledItem."
    )
    def save(self, *args, **kwargs):
        if self.scheduled_item and self.scheduled_item.dayprogram != self.dayprogram:
            raise ValueError("The Link's DayProgram must match the ScheduledItem's DayProgram.")
        super().save(*args, **kwargs)
 
    def __str__(self):
        return self.url or self.document.url


class Route(models.Model):
    dayprogram = models.ForeignKey(DayProgram, related_name='routes', on_delete=models.CASCADE)
    description = models.TextField()
    gpx_file = models.FileField(upload_to='gpx_files/')
    #uploaded_by

    def __str__(self):
        return self.description

class TripExpense(models.Model):
    CATEGORY_CHOICES = [
        ('', 'No Category'),
        ('Transportation', 'Transportation'),
        ('Lodging', 'Lodging'),
        ('Food and Drinks','Food and Drinks'),
        ('Activity', 'Activity'),
        ('Other', 'Other'),
    ]
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='expenses')
    tripper = models.ForeignKey(Tripper, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    converted_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10)
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=30, blank=True, null=True)
    receipt = models.ImageField(upload_to='receipts/', blank=True, null=True)
    category = models.CharField(max_length=20,choices=CATEGORY_CHOICES,blank=True,default='')
 
    def __str__(self):
        return f'{self.amount} {self.currency} on {self.trip.name} by {self.tripper.name}'

    def save(self, *args, **kwargs):
        default_currency = settings.APP_CURRENCY 

        if self.currency != default_currency:
            self.converted_amount = self.convert_to_default_currency()
        else:
            self.converted_amount = self.amount

        if self.receipt:
            img = PilImage.open(self.receipt)
            max_size = (600, 600)  
            img.thumbnail(max_size)
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=75)
            buffer.seek(0)
            self.receipt.save(self.receipt.name, ContentFile(buffer.read()), save=False)

        super(TripExpense, self).save(*args, **kwargs)

    def convert_to_default_currency(self):
        api_url = "https://v6.exchangerate-api.com/v6/" + settings.EXCHANGERATE_API_KEY + "/latest/" + self.currency 
        response = requests.get(api_url)

        if response.status_code == 200:
            data = response.json()
            conversion_rate = data['conversion_rates'].get(settings.APP_CURRENCY)

            if conversion_rate:
                return Decimal(self.amount) * Decimal(conversion_rate)

        return self.amount

class TripBudget(models.Model):
    CATEGORY_CHOICES = [
        ('', 'No Category'),
        ('Transportation', 'Transportation'),
        ('Lodging', 'Lodging'),
        ('Food and Drinks','Food and Drinks'),
        ('Activity', 'Activity'),
        ('Other', 'Other'),
    ]
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='budget')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    converted_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10)
    category = models.CharField(max_length=20,choices=CATEGORY_CHOICES,blank=True,default='')

    def __str__(self):
        return f'{self.amount} for {self.category} on {self.trip.name}'


class Location(models.Model):
    tripper = models.ForeignKey(Tripper, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField()

class ImmichPhotos(models.Model):
    tripper = models.ForeignKey(Tripper, on_delete=models.CASCADE)
    immich_photo_id  = models.CharField(max_length=100)  
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    city = models.CharField(max_length=100, null=True, blank=True)  
    timestamp = models.DateTimeField()
    thumbnail = models.ImageField(upload_to='immich_thumbnails/', null=True, blank=True)  


class ScheduledItem(models.Model):
    CATEGORY_CHOICES = [
        ('', 'No Category'),
        ('Transportation', 'Transportation'),
        ('Lodging', 'Lodging'),
        ('Food and Drinks','Food and Drinks'),
        ('Activity', 'Activity'),
        ('Other', 'Other'),
    ]
    TRANSPORTATION_TYPE_CHOICES = [
        ('', 'Not Specified'),
        ('Airplane', 'Airplane'),
        ('Bus', 'Bus'),
        ('Train','Train'),
        ('Taxi', 'Taxi'),
        ('Other', 'Other'),
    ]

    dayprogram = models.ForeignKey(DayProgram, on_delete=models.CASCADE, related_name='scheduled_items')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    start_address = models.CharField(max_length=255)
    end_address = models.CharField(max_length=255, blank=True, null=True)
    transportation_type = models.CharField(max_length=50, choices=TRANSPORTATION_TYPE_CHOICES,blank=True,null=True)

    def __str__(self):
        trip_date = self.dayprogram.tripdate.strftime("%d-%m-%Y") if self.dayprogram.tripdate else "No Date"
        return f"({self.start_time} - {self.end_time}) {self.get_category_display()} on {trip_date}" 


class TripperDocument(models.Model):
    CATEGORY_CHOICES = [
        ('', 'No Category'),
        ('Passport', 'Passport'),
        ('Visa', 'Visa'),
        ('Medical', 'Medical'),
        ('Insurance', 'Insurance'),
        ('Other', 'Other'),
    ]
    tripper = models.ForeignKey(Tripper, related_name='documents', on_delete=models.CASCADE)
    document = models.FileField(upload_to='tripper_documents/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True,
        default=''
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.tripper.name} - {self.category or 'No Category'}"



class InviteCode(models.Model):
    tribe = models.ForeignKey("Tribe", on_delete=models.CASCADE, related_name="invites")
    code = models.CharField(max_length=20, unique=True)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_code(cls, tribe):
        code = get_random_string(8).upper()
        return cls.objects.create(tribe=tribe, code=code)


class TripOutline(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="trip_outlines"
    )
    def __str__(self):
        return self.name or f"Outline {self.id}"


class TripOutlineItem(models.Model):
    outline = models.ForeignKey(TripOutline, on_delete=models.CASCADE, related_name="items")
    sequence = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    overnightlocation = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.sequence}: {self.description or 'No description'}"




class ItineraryIdea(models.Model):
    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="itinerary_ideas"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_itinerary_ideas"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ItineraryIdeaDay(models.Model):
    itineraryidea = models.ForeignKey(
        ItineraryIdea,
        on_delete=models.CASCADE,
        related_name="itineraryidea_days"
    )
    day_sequence = models.PositiveIntegerField()
    day_description = models.TextField(blank=True, null=True)
    day_possible_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["day_sequence"]

    def __str__(self):
        description = f" - {self.day_description}" if self.day_description else ""
        return f"{self.itineraryidea.name}, {self.day_sequence}{description}"

class DayLocation(models.Model):
    day = models.ForeignKey(
        ItineraryIdeaDay,
        on_delete=models.CASCADE,
        related_name="day_locations"
    )
    sequence = models.PositiveIntegerField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius = models.PositiveIntegerField(default=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.day.day_sequence}, Day {self.sequence} ({self.description})"


class OvernightLocation(models.Model):
    day = models.OneToOneField(
        ItineraryIdeaDay,
        on_delete=models.CASCADE,
        related_name="overnightlocation"
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius = models.PositiveIntegerField(default=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.day.day_sequence}, Overnight ({self.description})"
