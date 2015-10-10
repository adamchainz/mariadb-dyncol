#!/bin/bash -e

# Install MariaDB to replace the existing MySQL
sudo service mysql stop
sudo apt-get install -y python-software-properties
sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
sudo add-apt-repository "deb http://ftp.osuosl.org/pub/mariadb/repo/10.0/ubuntu precise main"
sudo apt-get update -qq
yes Y | sudo apt-get install -y mariadb-server libmariadbclient-dev
