from django.contrib import admin

from .models import Licence, LicenceKeyUsage, LicencePayment


admin.site.register(Licence)
admin.site.register(LicenceKeyUsage)
admin.site.register(LicencePayment)