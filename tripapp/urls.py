from django.urls import path
from . import views
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib import admin
from django.contrib.auth import views as auth_views

app_name = 'tripapp'

urlpatterns = [
    path('index', views.index, name='index'),
    path('', views.index, name='index'),
    path('home', views.trip_list, name='trip_list'),
    path('<uuid:tribe_id>/trip/create/', views.create_trip, name='create_trip'),
    path('trip/<slug:slug>/', views.trip_detail, name='trip_detail'),
    path('trip/<int:id>/trippers/', views.trip_trippers, name='trip_trippers'),
    path('trip/<int:trip_id>/tripper_list/', views.tripper_list, name='tripper_list'),
    path('trip/<int:trip_id>/tripper/<int:tripper_id>/badges/', views.trip_tripper_badges, name='trip_tripper_badges'),
    path('trip/<int:trip_id>/tripper/<int:tripper_id>/badgeassignments/', views.trip_tripper_badgeassignments, name='trip_tripper_badgeassignments'),
    path('trip/<int:id>/edit/', views.add_or_edit_trip, name='edit_trip'),
    path('trip/<int:trip_id>/add_checklist_item/', views.add_checklist_item, name='add_checklist_item'),
    path('trip/<int:trip_id>/map/', views.trip_map_view, name='trip_map_view'),
    path('trip/<int:trip_id>/bingocards/', views.trip_bingocards, name='trip_bingocards'),
    path('trip/<int:trip_id>/bingocardsadmin/', views.tripadmin_bingocards, name='tripadmin_bingocards'),
    path('trip/<int:trip_id>/bingocards/add/', views.add_bingocard, name='add_bingocard'),
    path('trip/<int:trip_id>/dayprogram/<int:dayprogram_id>/points/', views.trip_dayprogram_points, name='trip_dayprogram_points'),
    path('trip/<int:trip_id>/dayprograms/', views.trip_dayprograms, name='trip_dayprograms'),
    path('trip/<int:trip_id>/add_trippers/<uuid:tribe_id>/', views.add_trippers, name='add_trippers'),
    path('trip/<int:trip_id>/points/', views.trip_points, name='trip_points'),
    path('trip/<int:trip_id>/points/add/', views.add_point, name='add_point'),
    path('trip/<int:trip_id>/point/<int:point_id>/edit/', views.edit_point, name='edit_point'),
    path('trip/<int:trip_id>/point/<int:point_id>/delete/', views.delete_point, name='delete_point'),
    path('trip/<int:trip_id>/dayprogram/add/', views.dayprogram_add, name='dayprogram_add'),
    path('trip/<int:trip_id>/upload_route/', views.upload_route, name='upload_route'),
    path('trip/<int:trip_id>/route/<int:route_id>/delete/', views.delete_route, name='delete_route'),
    path('tripper/<int:tripper_id>/profile/', views.tripper_profile, name='tripper_profile'),
    path('tripper/<int:tripper_id>/badges/', views.tripper_badges, name='tripper_badges'),
    path('tripper/<int:tripper_id>/trip/<int:trip_id>/edit/', views.edit_tripper, name='edit_tripper'),
    path('dayprogram/<int:id>/', views.dayprogram_detail, name='dayprogram_detail'),
    path('dayprogram/<int:dayprogram_id>/add_image/', views.add_image, name='add_image'),
    path('dayprogram/<int:id>/check_answer/<int:questionid>/', views.check_answer, name='check_answer'),
    path('dayprogram/<int:dayprogram_id>/edit/', views.edit_dayprogram, name='edit_dayprogram'),
    path('dayprogram/<int:dayprogram_id>/questions', views.dayprogram_questions, name='dayprogram_questions'),
    path('dayprogram/<int:dayprogram_id>/questions/add/', views.add_question, name='add_question'),
    path('dayprogram/<int:dayprogram_id>/add_logentry/', views.add_logentry, name='add_logentry'),
    path('dayprogram/<int:dayprogram_id>/add-badge-and-question/', views.add_badge_and_question, name='add_badge_and_question'),
    path('dayprogram/<int:dayprogram_id>/add-link/', views.add_link, name='add_link'),
    path('dayprogram/<int:dayprogram_id>/add_suggestion/', views.add_suggestion, name='add_suggestion'),
    path('question/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('badges/', views.badge_list, name='badge_list'),
    path('mytribesbadges/', views.mytribes_badges_view, name='mytribes_badges_view'),
    path('badge_claimed/<int:badge_id>/', views.badge_claimed, name='badge_claimed'),
    path('upload_badge/', views.upload_badge, name='upload_badge'),
    path('checklist_item/<int:item_id>/toggle/', views.toggle_checklist_item, name='toggle_checklist_item'),
    path('toggle_checklist_item/<int:item_id>/', views.toggle_checklist_item, name='toggle_checklist_item'),
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('admin/', admin.site.urls),
    path('map/', views.map_view, name='map_view'),
    path('bingocard/<int:pk>/', views.bingocard_detail, name='bingocard_detail'),
    path('bingocard/<int:bingocard_id>/upload/', views.upload_answerimage, name='upload_answerimage'),
    #path('tribe/<uuid:tribe_id>/trips/', views.tribe_trips, name='tribe_trips'),
    path('organize', views.tribe_trips, name='tribe_trips'),
    path('organize/<uuid:tribe_id>/trip/<int:trip_id>/', views.tribe_trip_organize, name='tribe_trip_organize'),
    path('invite/', views.invite_to_tribe, name='invite_to_tribe'),
    path('register/invite/<uid>/', views.register_invite, name='register_invite'),
    path('tribe/create/', views.create_tribe, name='create_tribe'),
    path('permission_denied/', views.permission_denied, name='permission_denied'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('facilmap', views.facilmap, name='facilmap'),
    path('planner_map/<int:trip_id>/', views.planner_map, name='planner_map'),
    path('save_event/', views.save_event, name='save_event'),
 ]
