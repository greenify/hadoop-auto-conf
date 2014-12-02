hadoop-auto-fabric
==============

An easy way to setup a distributed hadoop
This should work on any distribution - however you might need to change the
package manager for the JAVA installation in the configuration.

## How to use

Steps to run:

1) Edit your client and masters in the `fabfile.py`
2) `fab -R master setup`
3) `fab -P -R client setup`
4) `fab -R master updateClients start`

## Dependenices

You need to have ssh and fabric installed.

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
