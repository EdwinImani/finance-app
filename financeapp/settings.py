from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY
SECRET_KEY = 'django-insecure-dl@2!*0p51!mcfh2=#o9yigkere1drj@bd#hltxk*0$2m#b)(&'

DEBUG = True

ALLOWED_HOSTS = [
    "finance-app-2-0usq.onrender.com",
    "localhost",
    "127.0.0.1",
    "nimadvr4.pythonanywhere.com",
]


# APPLICATIONS

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'users',
    'accounting',
    'products',
    'invoices',
    'partners',
    'purchase',
    'company',
]


# MIDDLEWARE

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# URLS

ROOT_URLCONF = 'financeapp.urls'


# TEMPLATES

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        # dossier templates global
        'DIRS': [BASE_DIR / "templates"],

        'APP_DIRS': True,

        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'financeapp.context_processors.company_branding',
            ],
        },
    },
]


# WSGI

WSGI_APPLICATION = 'financeapp.wsgi.application'


# DATABASE

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# PASSWORD VALIDATION

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# INTERNATIONALIZATION

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True
USE_TZ = True


# FORMAT DES DATES

DATE_FORMAT = "d/m/Y"
SHORT_DATE_FORMAT = "d/m/Y"
DATETIME_FORMAT = "d/m/Y H:i:s"
DATE_INPUT_FORMATS = ["%d/%m/%Y", "%Y-%m-%d"]

USE_L10N = False


# STATIC FILES

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"


# MEDIA FILES (images uploadées)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
