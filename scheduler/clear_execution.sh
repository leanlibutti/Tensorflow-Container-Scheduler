#/bin/bash
docker kill $(docker ps -q) 
docker container prune -f
output=$(pgrep -i python3)
sudo kill -9 $output
sudo rm Data/log/log-*
sudo rm Data/log/client_events_*   
sudo rm models/output_*