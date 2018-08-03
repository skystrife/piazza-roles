FROM python:3.6
RUN apt update
RUN apt install cmake -y
RUN groupadd web
RUN useradd -m -g web -s /bin/bash web
RUN pip install --no-cache-dir pipenv
RUN mkdir -p /srv/web
RUN chown web:web /srv/web
USER web
COPY --chown=web:web Pipfile /srv/web
COPY --chown=web:web Pipfile.lock /srv/web
COPY --chown=web:web vendor /srv/web/vendor
COPY --chown=web:web ext /srv/web/ext
WORKDIR /srv/web
RUN pipenv install
COPY --chown=web:web . /srv/web
EXPOSE 8000
CMD ["pipenv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--worker-class", "eventlet", "--workers", "1", "--reload", "roles.wsgi:app"]
