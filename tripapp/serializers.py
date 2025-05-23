# serializers.py
from rest_framework import serializers
from .models import Trip

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
