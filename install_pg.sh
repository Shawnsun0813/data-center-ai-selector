#!/bin/bash
set -e

echo "Updating APT packages..."
sudo apt-get update

echo "Installing PostgreSQL..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib

echo "Ensuring service is started..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

echo "Configuring postgres user password..."
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

echo "Checking if database exists, creating if not..."
DB_EXISTS=$(sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw site_selection ; echo $?)
if [ $DB_EXISTS -ne 0 ]; then
    sudo -u postgres psql -c "CREATE DATABASE site_selection;"
    echo "Database site_selection created."
else
    echo "Database site_selection already exists."
fi

echo "PostgreSQL setup complete!"
