#!/bin/bash
#
# Set access rights on DATASTAGE data file areas
#

source /root/datastageconfig.d/datastageconfig.sh

# chgrp "RGMember" /home/data
# chown test_datastage: DATASTAGE.README

# Add ACLs to prevent unauthenticated access?

mkdir -p /home/data/private
chown www-data: /home/data/private
chmod --recursive g+s /home/data/private

mkdir -p /home/data/shared
chown www-data: /home/data/shared
chmod --recursive g+s /home/data/shared

mkdir -p /home/data/collab
chown www-data: /home/data/collab
chmod --recursive g+s /home/data/collab


# End.