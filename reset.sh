#!/bin/sh
sudo docker compose down --rmi local -v
sudo rm data/matfyzgame.db
sudo docker compose up -d --build
