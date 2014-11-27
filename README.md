hadoop-auto-conf
================

A simple tool to setup your distributed Hadoop FS.
This should work on any distribution - however you might need to change the
package manager for the JAVA installation.

## Setup

0) Adjust the `Hadooper` 

* masterName
* masterIP
* masterKey

1) Copy the script to all of your nodes (e.g. scp)

2) Create a master run `./hadooper.sh 1`

3) Create a bunch of clients -> run `./hadooper.sh`

4) Update the master

4.1) Add all your clients to the `/etc/hosts`  
4.2) Add this list of slaves to `/opt/hadoop/etc/hadoop/slaves`  
4.3) Check whether you can ssh into all clients
  
5) Start Hadoop  
5.1) Run `hadoop namenode -format`    
5.2) Start the data nodes `stop-dfs.sh && start-dfs.sh`  
5.3) Start yarn `stop-yarn.sh && start-yarn.sh`  

6) Check the admin report `hadoop dfsadmin -report`

(tbd CURL script)

## Debug

```
/opt/hadoop/logs/hadoop-ubuntu-datanode-node1.log
/opt/hadoop/logs/hadoop-ubuntu-namenode-node1.log
/opt/hadoop/logs/yarn-ubuntu-nodemanager-node1.log
```

## Pitfalls

* Don't change the hostname - you need to delete the `VERSION` file (and restart all hdfs services)
* have multiple entries in your hostname conf -> `127.0.0.1 nodeX`
* wrong IP in your `/etc/hosts`
* wrong master in core-site (check also the master - must link to its public IP)
* clients are not in `/etc/hosts`
