#!/bin/bash


echo -e "\n\nStarting mongo"
echo "sudo systemctl start mongod"
sudo systemctl start mongod

sleep 5

echo -e "\n\nChecking mongo status"
echo "sudo systemctl status mongod"
sudo systemctl status mongod

exit 0
