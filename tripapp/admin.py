from django.contrib import admin
from .models import Trip, DayProgram, Tripper, Badge, Checklist, ChecklistItem, Image, Question, Point, BingoCard, BingoAnswer, BadgeAssignment, LogEntry, Link, Route
from django_q.tasks import async_task
from .models import Tribe, UserProfile, TripExpense

class PointAdmin(admin.ModelAdmin):
    list_display = ('name', 'trip')
    filter_horizontal = ('dayprograms',)  

def run_assign_badges(modeladmin, request, queryset):
    async_task('tripapp.tasks.assign_badges')
    modeladmin.message_user(request, "The assign_badges task has been executed.")

run_assign_badges.short_description = 'Run assign_badges task'

class BadgeAdmin(admin.ModelAdmin):
    actions = [run_assign_badges]



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
admin.site.register(Link)
admin.site.register(Route)
admin.site.register(TripExpense)
