# serializers.py
from rest_framework import serializers
from .models import Trip, LogEntryLike

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'


class TripMapDataSerializer(serializers.Serializer):
    name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    photo_url = serializers.URLField()
    trip_url = serializers.URLField()

class LogEntryLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntryLike
        fields = ['id', 'logentry', 'tripper', 'emoji', 'created_at']
        read_only_fields = ['created_at']