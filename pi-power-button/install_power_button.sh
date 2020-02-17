 #!/bin/bash

# Make both scripts executable
sudo chmod +x listen_for_shutdown.*

# Copy scripts to their respective directories
sudo cp listen_for_shutdown.py /usr/local/bin/
sudo cp listen_for_shutdown.sh /etc/init.d/

# Update rc.d to register the script to run at boot
sudo update-rc.d listen_for_shutdown.sh defaults

# Start the script so that it functions on this boot as well.
sudo /etc/init.d/listen_for_shutdown.sh start
