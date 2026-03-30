from django.db import models

class Partner(models.Model):

    PARTNER_TYPES = (
    ('importer', 'Importer'),
    ('seller', 'Seller'),
    ('requester', 'Requester'),
    ('enduser', 'End User'),
    )

    description = models.CharField(max_length=255)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPES)

    email = models.EmailField(blank=True)
    fax = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return f"{self.description}"
    
    
    
class PartnerAddress(models.Model):
    partner = models.ForeignKey(
        Partner,
        related_name="addresses",
        on_delete=models.CASCADE
    )
    address = models.CharField(max_length=255)

    def __str__(self):
        return self.address
    
    
class PartnerPhone(models.Model):
    partner = models.ForeignKey(
        Partner,
        related_name="phones",
        on_delete=models.CASCADE
    )
    phone_number =models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.phone_number or "No phone"