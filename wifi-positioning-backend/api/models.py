from django.db import models
from rest_framework import status
import uuid, math
from django.contrib.auth.models import User

# Create your models here.
class WiFiData(models.Model):
    wifi_data_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, unique=True)
    ssid = models.CharField(max_length=255)
    bssid = models.CharField(max_length=17)
    rssi = models.IntegerField()
    x = models.FloatField()
    y = models.FloatField()
    #  data type 0 = training, 1 = validation, 2 = test
    data_type = models.FloatField(default=0)

class EmailVerificationTokens(models.Model):
    token_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, unique=True)
    user_id = models.CharField(max_length=200)
    token = models.CharField(max_length=255)
    expired_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    last_created_date = models.DateTimeField(auto_now_add=True)

class ResponseModel:
    @classmethod
    def success_pagging(cls, data, message="Success", page_size=10, total=0, page_number=0):
        return {
            "success": True,
            "code": status.HTTP_200_OK,
            "message": message,
            "data": data,
            "page": {
                "page_size": page_size,
                "total": total,
                "page_count": math.ceil(total / page_size),
                "page_number": page_number
            }
        }

    @classmethod
    def success(cls, data, message="Success"):
        return {
            "success": True,
            "code": status.HTTP_200_OK,
            "message": message,
            "data": data
        }

    @classmethod
    def error(cls, message, code=status.HTTP_400_BAD_REQUEST):
        return {
            "success": False,
            "code": code,
            "message": message,
            "data": None,
            "page": {
                "size": 0,
                "total": 0,
                "totalPages": 0,
                "current": 0
            }
        }