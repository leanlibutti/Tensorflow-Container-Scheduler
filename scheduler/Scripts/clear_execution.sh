#/bin/bash
docker kill $(docker ps -q) 
docker container prune -f
output=$(pgrep -i python3)
kill -9 $output
rm ../Data/log/log-*
rm ../Data/log/client_events_*   
rm ../models/output_*