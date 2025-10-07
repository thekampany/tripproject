# serializers.py
from rest_framework import serializers
from .models import Trip, LogEntryLike

from .models import TripOutline, TripOutlineItem


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


class TripOutlineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripOutlineItem
        fields = ["sequence", "description", "latitude", "longitude", "radius"]

class TripOutlineSerializer(serializers.ModelSerializer):
    items = TripOutlineItemSerializer(many=True)

    class Meta:
        model = TripOutline
        fields = ["id", "name", "items"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        outline = TripOutline.objects.create(**validated_data)
        for item_data in items_data:
            TripOutlineItem.objects.create(outline=outline, **item_data)
        return outline
