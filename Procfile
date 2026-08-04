release: python manage.py migrate --noinput
web: python manage.py migrate --noinput && gunicorn financeapp.wsgi:application --log-file -
