#!/bin/bash

# Script to set up a Django project on Vagrant.

# Installation settings

PROJECT_NAME=$1

DB_NAME=$PROJECT_NAME
VIRTUALENV_NAME=$PROJECT_NAME

PROJECT_DIR=/home/vagrant/$PROJECT_NAME
VIRTUALENV_DIR=/home/vagrant/.virtualenvs/$PROJECT_NAME

PGSQL_VERSION=9.1
NODEJS_VERSION=0.10.23

# Need to fix locale so that Postgres creates databases in UTF-8
cp -p $PROJECT_DIR/etc/install/etc-bash.bashrc /etc/bash.bashrc
locale-gen en_GB.UTF-8
dpkg-reconfigure locales

export LANGUAGE=en_GB.UTF-8
export LANG=en_GB.UTF-8
export LC_ALL=en_GB.UTF-8

# Install essential packages from Apt
apt-get update -y

# Python dev packages
apt-get install -y build-essential python python-dev python-setuptools python-pip

# Dependencies for freezr
apt-get install -y libsqlite3-dev rabbitmq-server

# Git (we'd rather avoid people keeping credentials for git commits in
# the repo, but sometimes we need it for pip requirements that aren't
# in PyPI)
apt-get install -y git

# And some other, not essential for development but otherwise useful
apt-get install -y zsh tmux

# Postgresql
if ! command -v psql; then
    apt-get install -y postgresql-$PGSQL_VERSION libpq-dev
    cp $PROJECT_DIR/etc/install/pg_hba.conf /etc/postgresql/$PGSQL_VERSION/main/
    /etc/init.d/postgresql reload
fi

# virtualenv global setup
if ! command -v pip; then
    easy_install -U pip
fi

pip install virtualenv virtualenvwrapper stevedore virtualenv-clone

# shell environment global setup
cp -p $PROJECT_DIR/etc/install/bashrc /home/vagrant/.bashrc
cp -p $PROJECT_DIR/etc/install/zshrc /home/vagrant/.zshrc
su - vagrant -c "mkdir -p /home/vagrant/.pip_download_cache"

# Node.js, CoffeeScript and LESS -- use distribution version as
# packaged ubuntu 12.04 nodejs version is old.
if ! command -v npm; then
    wget http://nodejs.org/dist/v${NODEJS_VERSION}/node-v${NODEJS_VERSION}.tar.gz
    tar xzf node-v${NODEJS_VERSION}.tar.gz
    cd node-v${NODEJS_VERSION}/
    ./configure && make && make install
    cd ..
    rm -rf node-v${NODEJS_VERSION}/ node-v${NODEJS_VERSION}.tar.gz
fi
if ! command -v coffee; then
    npm install -g coffee-script
fi
if ! command -v lessc; then
    npm install -g less
fi

# ---

# postgresql setup for project
createdb -Upostgres $DB_NAME

# virtualenv setup for project
su - vagrant -c "/usr/local/bin/virtualenv $VIRTUALENV_DIR && \
    echo $PROJECT_DIR > $VIRTUALENV_DIR/.project && \
    PIP_DOWNLOAD_CACHE=/home/vagrant/.pip_download_cache $VIRTUALENV_DIR/bin/pip install -r $PROJECT_DIR/requirements.txt && \
    PIP_DOWNLOAD_CACHE=/home/vagrant/.pip_download_cache $VIRTUALENV_DIR/bin/pip install virtualenvwrapper \
"

echo "workon $VIRTUALENV_NAME" >> /home/vagrant/.bashrc
echo "workon $VIRTUALENV_NAME" >> /home/vagrant/.zshrc

sudo chsh -s /bin/zsh vagrant

# Set execute permissions on manage.py, as they get lost if we build
# from a zip file
chmod a+x $PROJECT_DIR/manage.py

# Django project setup
#su - vagrant -c "source $VIRTUALENV_DIR/bin/activate && cd $PROJECT_DIR && ./manage.py syncdb --noinput && ./manage.py migrate"
su - vagrant -c "source $VIRTUALENV_DIR/bin/activate && cd $PROJECT_DIR && ./manage.py syncdb --noinput"
