#! /bin/bash

cd /home/pi/species_survey

# Get latest commit
git pull
git log --oneline -n 1 > this_commit.log

if [ ! -f boot_commit.log ]; then
        echo "Missing boot_commit.log so copying from this_commit.log"
        cp this_commit.log boot_commit.log
fi 

cmp this_commit.log boot_commit.log
if [ $? -ne 0 ]; then
        mv this_commit.log boot_commit.log
        echo "Time to reboot"
       sudo reboot
fi
