#!/bin/bash

# note this whole script will be executed as root

# download the latest dsbench binary release
curl -s https://api.github.com/repos/datastax/dsbulk/releases/latest \
| grep "browser_download_url.*dsbulk-.*\.tar\.gz\"$" \
| cut -d '"' -f 4 \
| wget -qi -

tar -zxvf dsbulk*.tar.gz

