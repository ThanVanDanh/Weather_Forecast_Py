from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    phone = models.CharField(max_length=20, verbose_name='Số điện thoại', blank=True)

    address = models.CharField(max_length=255, verbose_name='Địa chỉ hiện tại', blank=True, null=True)
    latitude = models.FloatField(verbose_name='Vĩ độ', blank=True, null=True)
    longitude = models.FloatField(verbose_name='Kinh độ', blank=True, null=True)
    def __str__(self):
        return f"{self.user.username} - {self.phone}"