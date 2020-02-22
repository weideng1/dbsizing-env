#!/bin/bash

curl -s https://api.github.com/repos/datastax/dsbench-labs/releases/latest \
| grep "browser_download_url.*dsbench\"$" \
| cut -d '"' -f 4 \
| wget -qi -
