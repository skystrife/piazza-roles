# Piazza Role Discovery

This repository is a demonstration of using a Mixture of
Dirichlet-Multinomial Mixtures for role discovery on Piazza courses.

## Installation

```bash
git clone https://github.com/skystrife/piazza-roles.git
cd piazza-roles
git submodule update --init --recursive
```

You will need to create two `.env` files to set environment variables
properly:

## Configuration

### Root `.env`
Here you should set the environment variables for the Postgres database
container:

1. `POSTGRES_USER=nonrootuseryouwanttouse`
2. `POSTGRES_PASSWORD=passwordtoconnecttodb`

### `web/.env`
Here you should set the environment variables for the Flask application
container:

1. `SECRET_KEY=somespecialsecret`
2. `FLASK_ENV=(development|production)`
3. `SQLALCHEMY_DATABASE_URI="postgresql://POSTGRESUSERHERE@POSTGRESPASSWORDHERE@postgres:5432/POSTGRESUSERHERE"`
4. `SQLALCHEMY_TRACK_MODIFICATIONS=false`
5. `CELERY_BROKER_URL="redis://redis:6379/0"`
6. `CELERY_RESULT_BACKEND="redis://redis:6379/0"`
7. `SOCKETIO_MESSAGE_QUEUE="redis://redis"`

## Running

```bash
# Build containers:
sudo docker-compose build

# Run containers:
sudo docker-compose up

# Bootstrap the db while the app is running:
sudo docker-compose exec web pipenv run flask db upgrade
```
