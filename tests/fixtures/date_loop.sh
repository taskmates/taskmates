#!/bin/bash

# Trap INT signal and ignore it
trap '' INT

# Infinite loop
while true; do
    date  # Print the current date and time
    sleep 5  # Wait for 5 seconds
done
