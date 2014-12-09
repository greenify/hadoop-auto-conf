from fabric.api import run, env, prefix, sudo, cd, settings
from cuisine import *

masterIPFile = "master.ip"

def mesos():
    package_ensure('mesos')
    package_ensure('mesosphere')
    masterIP = getMasterIP()
    with mode_sudo():
        file_write("/etc/mesos/zk", "zk://%s:2181/mesos\n" % masterIP)
        if "master" in env.roles:
            file_write("/etc/zookeeper/conf/myid", "1\n")
            file_write("/etc/mesos-master/ip", "%s\n" % masterIP)
            file_write("/etc/mesos-master/hostname", "%s\n" % masterIP)
            dir_ensure("/etc/marathon/conf")
            file_write("/etc/marathon/conf/hostname", "%s\n" % masterIP)
            file_write("/etc/marathon/conf/master", "zk://%s:2181/mesos\n" % masterIP)
            file_write("/etc/marathon/conf/zk", "zk://%s:2181/marathon\n" % masterIP)
            with settings(warn_only=True):
                sudo("stop zookeeper")
                sudo("stop mesos-master")
                sudo("stop marathon")
            sudo("start zookeeper")
            sudo("start mesos-master")
            sudo("start marathon")
        else:
            file_write("/etc/mesos-slave/ip", "%s\n" % getIP())
            file_write("/etc/mesos-slave/hostname", "%s\n" % getIP())
            with settings(warn_only=True):
                sudo("stop mesos-slave")
            sudo("start mesos-slave")

def getMasterIP():
    if 'masterIP' not in env:
        with open(masterIPFile, "r") as file:
            env.masterIP = file.read()
    return env.masterIP


def getIP():
    return run("ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'")
