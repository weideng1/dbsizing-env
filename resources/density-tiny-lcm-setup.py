#!/usr/bin/env python
# Example provisioning API usage script.  (C) DataStax, 2015.  All Rights Reserved
#
# Needs these OS environmental variables pre-defined: lcm_server, dsrepo_user, dsrepo_pass, opscenter_session (optional), dse_ver (optional), cluster_name (optional)
# command line parameter with node IP/DC in the following format:
# public_IP:private_IP:DC_name:node_number
#
# An example command line to generate from ctool output is like the following:
# ctool info --private-ips <ctool_cluster_name> | tr " " "\n" | awk '{print $1 ":" $1 ":dc1:" NR-1}'
#
import os
import sys
import requests
import json
import threading

# Configurable Global variables
if "lcm_server" not in os.environ:
    print "Cannot find lcm_server in env"
    exit(1)
server_ip = os.environ.get('lcm_server').strip()
base_url = 'http://%s:8888/api/v2/lcm/' % server_ip

if "dsrepo_user" not in os.environ or "dsrepo_pass" not in os.environ:
    print "Cannot find dsrepo_user and dsrepo_pass in env"
    exit(1)
repo_user = os.environ.get('dsrepo_user').strip()
repo_pass = os.environ.get('dsrepo_pass').strip()

opscenter_session = os.environ.get('opscenter_session', '')

dse_ver = os.environ.get('dse_ver', '6.7.7').strip()

cluster_name = os.environ.get('cluster_name', 'dse-cluster').strip()

print str(sys.argv)

def do_post(url, post_data):
    result = requests.post(base_url + url,
                           data=json.dumps(post_data),
                           headers={'Content-Type': 'application/json', 'opscenter-session': opscenter_session})
    print repr(result.text)
    result_data = json.loads(result.text)
    return result_data

repository_response = do_post("repositories/",
    {"name": "dse-public-repo",
        "username": repo_user,
        "password": repo_pass,
        "repo-url": "http://debian.datastax.com/enterprise/",
        "repo-key-url": "https://debian.datastax.com/debian/repo_key"})

repository_id = repository_response['id']

# ssh private key example
with open('dense_node_general_key', 'r') as myfile:
        privateKey=myfile.read()
machine_credential_response = do_post("machine_credentials/",
     {"name": "node-key",
      "login-user": "ubuntu",
      "become-mode": "sudo",
      "use-ssh-keys": True,
      "ssh-private-key": privateKey
    }
)
machine_credential_id = machine_credential_response['id']

cluster_profile_response = do_post("config_profiles/",
    {"name": cluster_name,
     "datastax-version": dse_ver,
     "json" : {
        "dse-yaml" : {
           "cql_slow_log_options" : {
              "enabled" : False
           },
           "enable_health_based_routing" : False,
           "authentication_options" : {
              "enabled" : False
           }
        },
        "jvm-options" : {
           "log_gc" : True,
           "number_of_gc_log_files" : 20,
           "max_heap_size" : "8g",
           "jmx-connection-type" : "remote-no-auth",
           "additional-jvm-opts" : [
                  "-Ddse.io.aio.enabled=false"
               ],
           "initial_heap_size" : "8g"
        },
        "logback-xml" : {
           "loggers" : [
              {
                 "level" : "INFO",
                 "name" : "com.thinkaurelius.thrift"
              }
           ]
        },
        "cassandra-yaml" : {
           "compaction_throughput_mb_per_sec" : 16,
           "allocate_tokens_for_local_replication_factor" : 3,
           "num_tokens" : 8,
           "concurrent_compactors" : 1,
           "tpc_cores" : 2,
           "endpoint_snitch" : "org.apache.cassandra.locator.GossipingPropertyFileSnitch",
           "file_cache_size_in_mb" : 512,
           "phi_convict_threshold" : 12,
           "hinted_handoff_throttle_in_kb" : 5120
        },
        "10-write-prom-conf" : {
           "enabled" : True
        }
     },
     "comment": 'LCM provisioned %s' % cluster_name})
cluster_profile_id = cluster_profile_response['id']

make_cluster_response = do_post("clusters/",
    {"name": cluster_name,
     "repository-id": repository_id,
     "machine-credential-id": machine_credential_id,
     "config-profile-id": cluster_profile_id})
cluster_id = make_cluster_response['id']

data_centers = set()
for host in sys.argv[1:]:
    data_centers.add(host.split(":")[2])

data_center_ids = {}
for data_center in data_centers:
    make_dc_response = do_post("datacenters/",
        {"name": data_center,
         "cluster-id": cluster_id,
         "solr-enabled": False,
         "spark-enabled": False,
         "graph-enabled": False})
    dc_id = make_dc_response['id']
    data_center_ids[data_center] = dc_id

for host in sys.argv[1:]:
    node_ip = host.split(":")[0]
    private_ip = host.split(":")[1]
    data_center = host.split(":")[2]
    node_idx = host.split(":")[3]
    seed_node = False
    if int(node_idx) < 1:
        seed_node = True
    make_node_response = do_post("nodes/",
        {"name": "node" + str(node_idx) + "_" + node_ip,
         "listen-address": private_ip,
         "native-transport-address": "0.0.0.0",
	 "broadcast-address": node_ip,
         "native-transport-broadcast-address": node_ip,
         "ssh-management-address": node_ip,
         "seed": seed_node,
         "datacenter-id": data_center_ids[data_center],
         "rack": "rack1"})

# Request an install job to execute the installation and configuration of the
# cluster. Until this point, we've been describing future state. Now LCM will
# execute the changes necessary to achieve that state.
install_job = do_post("actions/install",
                     {"job-type":"install",
                      "job-scope":"cluster",
                      "resource-id":cluster_id,
                      "continue-on-error":"false"})

print("http://%s:8888" % server_ip)


