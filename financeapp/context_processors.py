from company.models import CompanySetting


def company_branding(request):
    company = CompanySetting.objects.first()
    if not company:
        return {
            "company_brand_name": "",
            "company_brand_logo_url": "",
        }

    logo_url = company.company_logo.url if company.company_logo else ""
    return {
        "company_brand_name": company.company_name,
        "company_brand_logo_url": logo_url,
    }
