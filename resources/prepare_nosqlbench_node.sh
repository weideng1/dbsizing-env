#!/bin/bash

# note this whole script will be executed as root

# download the latest dsbench binary release
curl -s https://api.github.com/repos/datastax/dsbench-labs/releases/latest \
| grep "browser_download_url.*dsbench\"$" \
| cut -d '"' -f 4 \
| wget -qi -

cat <<EOF >> /home/ubuntu/.bash_history
./dsbench start type=cql yaml=baselines/cql-iot tags=phase:schema host=node0
./dsbench start type=cql yaml=baselines/cql-iot tags=phase:rampup host=node0 threads=auto cycles=1000000000 --report-graphite-to metrics:9109 --progress console:1m -v
EOF

cat <<EOF >> /home/ubuntu/.ssh/config
Host metrics
    StrictHostKeyChecking no
Host node*
    StrictHostKeyChecking no
EOF
