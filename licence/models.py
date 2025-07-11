from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
class Licence(models.Model):
    key = models.CharField(max_length=100)

    def __str__(self):
        return self.key

class LicenceKeyUsage(models.Model):
    licence = models.ForeignKey(Licence, on_delete=models.CASCADE, related_name='licence_key_usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='licence_key_usages')

    created_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.username



class LicencePayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='licence_payments')
    licence = models.ForeignKey(Licence, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=100)
    payment_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.username
    
    