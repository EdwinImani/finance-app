release: python manage.py migrate --noinput
web: gunicorn financeapp.wsgi:application --log-file -
