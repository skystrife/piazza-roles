# Piazza Role Discovery

This repository is a demonstration of using a Mixture of
Dirichlet-Multinomial Mixtures for role discovery on Piazza courses.

## Installation

```bash
git clone https://github.com/skystrife/piazza-roles.git
cd piazza-roles
git submodule update --init --recursive
sudo docker-compose build

# Run with:
sudo docker-compose up

# Bootstrap the db while the app is running with:
sudo docker-compose exec web pipenv run flask db upgrade
```
