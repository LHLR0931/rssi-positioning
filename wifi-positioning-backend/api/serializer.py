from rest_framework import serializers
from django.contrib.auth.models import User
from api.models import WiFiData

class UserSerializer(serializers.ModelSerializer):
    class Meta(object):
        model=User
        fields = ['id', 'username', 'email', 'first_name','is_staff', 'is_active']

class WifiDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WiFiData
        fields = '__all__'
        extra_kwargs = {
            'ssid': {'required': False, 'allow_blank': True}
        }

class DistinctXYSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()