#!/bin/sh

# This file is launched by policykit as root to be able to apply the settings
# which require more permissions as the current user

# All it does is copy the generated settings file to /etc and then the service will
# apply the settings with root permissions

mkdir -p "/etc/danctnix-tweaks"
mv "$1" "/etc/danctnix-tweaks/tweakd.conf"
service danctnix-tweakd restart