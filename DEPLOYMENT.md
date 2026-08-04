# Deployment Checklist

1. Set environment variables from `.env.example`.
2. Use a PostgreSQL database and set `DATABASE_URL` or `DB_*` variables.
3. Run `python manage.py migrate`.
4. Run `python manage.py collectstatic --noinput`.
5. Start the app with `python manage.py migrate --noinput && gunicorn financeapp.wsgi:application --log-file -` so the database schema is updated before Django serves requests.
6. Add the final domain to `DJANGO_ALLOWED_HOSTS`.
7. Add `https://your-domain` to `DJANGO_CSRF_TRUSTED_ORIGINS`.
8. Serve uploaded media from the host's persistent storage, object storage, or a web server path.

Do not commit real secrets, database passwords, or production `.env` files.
