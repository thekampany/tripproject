from django.contrib import admin
from .models import Trip, DayProgram, Tripper, Badge, Checklist, ChecklistItem, Image, Question, Point, BingoCard, BingoAnswer, BadgeAssignment, LogEntry, Link, Route
from django_q.tasks import async_task
from .models import Tribe, UserProfile, TripExpense, Location, ImmichPhotos, ScheduledItem
from django.core.management import call_command
from django_q.models import Schedule 

class PointAdmin(admin.ModelAdmin):
    list_display = ('name', 'trip')
    filter_horizontal = ('dayprograms',)  

def run_assign_badges(modeladmin, request, queryset):
    async_task('tripapp.tasks.assign_badges')
    modeladmin.message_user(request, "The assign_badges task has been executed.")
run_assign_badges.short_description = 'Run assign_badges task'

class BadgeAdmin(admin.ModelAdmin):
    actions = [run_assign_badges]

class LinkAdmin(admin.ModelAdmin):
    list_display = ('dayprogram', 'category', 'url', 'description','scheduled_item')
    list_filter = ('category',)

class ScheduledItemAdmin(admin.ModelAdmin):
    list_display = ('category', 'start_time', 'end_time', 'dayprogram')
    list_filter = ('type', 'dayprogram')

schedule_admin = admin.site._registry.get(Schedule)


def run_fetch_locations(modeladmin, request, queryset):
    call_command('run_fetch_locations')
    modeladmin.message_user(request, "fetch_locations_for_tripper task executed successfully.")
run_fetch_locations.short_description = 'Run fetch_locations_for_tripper now'

def run_fetch_and_store_immich_photos(modeladmin, request, queryset):
    call_command('run_fetch_and_store_immich_photos')  
    modeladmin.message_user(request, "fetch_and_store_immich_photos task executed successfully.")
run_fetch_and_store_immich_photos.short_description = 'Run fetch_and_store_immich_photos now'

if schedule_admin:
    schedule_admin.actions = (
        schedule_admin.actions + [run_fetch_locations, run_fetch_and_store_immich_photos]
        if schedule_admin.actions else
        [run_fetch_locations, run_fetch_and_store_immich_photos]
    )

class ImmichAdmin(admin.ModelAdmin):
    actions = [run_fetch_locations, run_fetch_and_store_immich_photos]


admin.site.register(Trip)
admin.site.register(DayProgram)
admin.site.register(Tripper)
admin.site.register(Badge, BadgeAdmin)
admin.site.register(Checklist)
admin.site.register(ChecklistItem)
admin.site.register(Image)
admin.site.register(Question)
admin.site.register(Point,PointAdmin)
admin.site.register(BingoCard)
admin.site.register(BingoAnswer)
admin.site.register(BadgeAssignment)
admin.site.register(Tribe)
admin.site.register(UserProfile)
admin.site.register(LogEntry)
admin.site.register(Link,LinkAdmin)
admin.site.register(Route)
admin.site.register(TripExpense)
admin.site.register(Location)
admin.site.register(ImmichPhotos,ImmichAdmin)
admin.site.register(ScheduledItem)