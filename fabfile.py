from fabric.api import run, env, prefix, sudo, cd, settings
from cuisine import *
from mesos import mesos
import re
from os import path
#import logging ; logging.basicConfig(level=logging.DEBUG)

env.roledefs = {
    'master': ['mesos-waterm'],
    'client': ['mesos-water1', 'mesos-water2']
}

##
# An easy way to setup a distributed hadoop
# You might need to edit the clients
#
# Steps to run:
# 1) fab -R master setup
# 2) fab -P -R client setup
# 3) fab -R master updateClients start
##

# settings
hadoopFile = "hadoop-2.5.2"
installDir = "/opt/hadoop"
storeDir = "/opt/hadoop_store"
userName = "hadoop"
mirrorURL = "http://apache.mirror.iphh.net/hadoop/common/"

# use apt
select_package("apt")

# auto
JAVA_HOME = "/usr/lib/jvm/java-7-openjdk-amd64"
configDir = installDir + "/etc/hadoop"
keyFile = "keyfile.ssh"
clientFile = "clients.ips"
masterIPFile = "master.ip"
sshFile = "/home/%s/.ssh/config" % userName


def install():
    initDir()

    fixHostname()

    package_update()
    package_ensure('openjdk-7-jdk')

    if not file_exists(hadoopFile + ".tar.gz"):
        print("downloading hadoop")
        run("wget " + mirrorURL + hadoopFile + "/" + hadoopFile + ".tar.gz")

    print("unpacking hadoop")
    run("tar xfz " + hadoopFile + ".tar.gz")

    print('setting user %s' % userName)

    user_ensure(userName, shell="/bin/bash")
    group_ensure(userName)
    print("initing installDir")
    with mode_sudo():
        dir_remove(installDir)
        dir_ensure(path.dirname(installDir))
        dir_ensure(storeDir)
        run("mv " + hadoopFile + " " + installDir)
        dir_attribs(installDir, owner=userName, group=userName, recursive=True)
        dir_attribs(storeDir, owner=userName, group=userName, recursive=True)
    print("hadoop at target")

    print("ensuring ssh key")
    if isMaster():
        pubkey = ""
        with mode_sudo():
            keyPath = ssh_keygen(userName, keytype="rsa")
            pubkey = file_read(keyPath)
        with open(keyFile, "w+") as file:
            file.write(pubkey)
        print("key saved")
    else:
        with open(keyFile, "r") as file:
            pubkey = file.read().replace('\n', '')

    with mode_sudo():
        ssh_authorize(userName, pubkey)


def fixHostname():
    print('fixing /etc/hosts (virtual ubuntu)')
    hostName = run("hostname")
    print(hostName)
    with settings(warn_only=True):
        sudo("! grep %s /etc/hosts && echo %s %s >> /etc/hosts" % (hostName, getIP(), hostName))


def getIP():
    return run("ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'")


def etc_hosts():
    hostName = run("hostname")
    ipAdress = getIP()
    if isMaster():
        env.masterIP = ipAdress
        with open(masterIPFile, "w") as file:
            file.write(ipAdress)
    else:
        lines = []
        if os.path.exists(clientFile):
            with open(clientFile, "r") as file:
                lines = file.read().split("\n")

        line = "%s %s" % (ipAdress, hostName)
        if line not in lines:
            lines.append(line)

        with open(clientFile, "w") as file:
            file.write('\n'.join(filter(lambda x: len(x) > 1, lines)))


def bashrc():
    lines = [
        "export JAVA_HOME=%s" % JAVA_HOME,
        "export HADOOP_INSTALL=" + installDir,
        "export PATH=$PATH:$HADOOP_INSTALL/bin",
        "export PATH=$PATH:$HADOOP_INSTALL/sbin",
        "export HADOOP_MAPRED_HOME=$HADOOP_INSTALL",
        "export HADOOP_COMMON_HOME=$HADOOP_INSTALL",
        "export HADOOP_HDFS_HOME=$HADOOP_INSTALL",
        "export YARN_HOME=$HADOOP_INSTALL",
        "export HADOOP_COMMON_LIB_NATIVE_DIR=$HADOOP_INSTALL/lib/native"]

    profileName = '/etc/profile.d/hadoop'
    file_write(profileName, '\n'.join(lines), mode='755', owner='root', group='root')

    file_update('/root/.bashrc', lambda _: text_ensure_line(_, 'source %s' % profileName))
    file_update('/home/%s/.bashrc' % userName, lambda _: text_ensure_line(_, 'source %s' % profileName))


def javaHome():
    file_update(configDir + '/hadoop-env.sh', lambda _: re.sub('\$\{JAVA_HOME\}', JAVA_HOME, _))
    line = "export JAVA_HOME=%s" % JAVA_HOME


def sshrc():
    line = "StrictHostKeyChecking no"

    with mode_sudo():
        file_ensure(sshFile)
        file_update(sshFile, lambda _: text_ensure_line(_, line))


def hdSiteConf():
    siteConfig = "\n<property>\n\t<name>fs.default.name</name>\n"
    siteConfig += "\t<value>hdfs://%s:9000</value>\n</property>" % (getMasterIP())
    file_update(configDir + '/core-site.xml', lambda _:
        re.sub('(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)', siteConfig, _))
    dir_ensure(storeDir + "/hdfs/datanode", recursive=True, owner=userName, group=userName)


def hdYarnConf():
    yarnConfig = """
<property>
    <name>yarn.nodemanager.aux-services</name>
    <value>mapreduce_shuffle</value>
</property>
<property>
    <name>yarn.nodemanager.aux-services.mapreduce.shuffle.class</name>
    <value>org.apache.hadoop.mapred.ShuffleHandler</value>
</property>"""

    yarnConfig += "\n<property>\n\t<name>yarn.resourcemanager.hostname</name>\n"
    yarnConfig += "\t<value>%s</value>\n" % (getMasterIP())
    yarnConfig += "\t<description>Master resource manager</description>\n</property>"

    file_update(configDir + '/yarn-site.xml', lambda _:
        re.sub('(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)', yarnConfig, _))


def hdMapRedConf():
    run("cp %s %s" % (configDir + "/mapred-site.xml.template", configDir + "/mapred-site.xml"))
    mapConfig = "\n<property>\n\t<name>mapreduce.framework.name</name>\n"
    mapConfig += "\t<value>yarn</value>\n</property>"
    file_update(configDir + '/mapred-site.xml', lambda _:
        re.sub('(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)', mapConfig , _))


def hdfsConf():
    dir_ensure(storeDir + "/hdfs/datanode", recursive=True)
    hdfsConfig = """
<property>
    <name>dfs.replication</name>
    <value>1</value>
</property>"""

    hdfsConfig = "\n<property>\n\t<name>dfs.datanode.data.dir</name>\n"
    hdfsConfig += "\t<value>file://%s/hdfs/datanode</value>\n</property>" % (storeDir)

    if "master" in env.roles:
        dir_ensure(storeDir + "/hdfs/namenode", recursive=True, owner=userName, group=userName)

        hdfsConfig += "\n<property>\n\t<name>dfs.namenode.name.dir</name>\n"
        hdfsConfig += "\t<value>file://%s/hdfs/namenode</value>\n</property>" % (storeDir)

    # update conf
    file_update(configDir + '/hdfs-site.xml', lambda _:
        re.sub('(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)', hdfsConfig, _))

    if "master" in env.roles:
        jh = "JAVA_HOME=%s " % JAVA_HOME
        user("echo 'Y' |" + jh + "%s/bin/hdfs namenode -format" % (installDir))


def start():
    with mode_user(userName):
        startNode()
        startYarn()


def startNode():
    if "master" in env.roles:
        with prefix('source /etc/profile.d/hadoop '):
            nodeMgr = run("pgrep -f nodemanager")
            if len(nodeMgr) is 0:
                user("%s/sbin/start-dfs.sh" % (installDir))
            else:
                user("%s/sbin/stop-dfs.sh" % (installDir))
                user("%s/sbin/start-dfs.sh" % (installDir))

def startYarn():
    if "master" in env.roles:
        with prefix('source /etc/profile.d/hadoop '):
            yarn = run("pgrep -f yarn")
            if len(yarn) is 0:
                user("%s/sbin/start-yarn.sh" % (installDir))
            else:
                user("%s/sbin/stop-yarn.sh" % (installDir))
                user("%s/sbin/start-yarn.sh" % (installDir))


def hdfsTest():
    with cd("/tmp"):
        if not file_exists('/tmp/pg4300.txt'):
            run('wget http://www.gutenberg.org/cache/epub/4300/pg4300.txt')

        with prefix('source /etc/profile.d/hadoop '):
            with settings(warn_only=True):
                user('hdfs dfs -rm -r /test')
                user('hdfs dfs -mkdir /test')
                user('hdfs dfs -rm -r /out')
            user('hdfs dfs -copyFromLocal pg4300.txt /test/pg4300.txt')
            user('hdfs dfs -ls /test')
            user('hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-2.5.2.jar wordcount /test /out')
            user('hdfs dfs -rm -r /test')
            user('hdfs dfs -cat /out/part-r-00000 | head')
            user('hdfs dfs -rm -r /out')


def config():
    with mode_user(userName):
        bashrc()
        sshrc()
        etc_hosts()
        javaHome()
        hdSiteConf()
        hdYarnConf()
        hdMapRedConf()
        hdfsConf()

    print("you rock!")


def setup():
    install()
    config()


def user(command):
    return sudo(command, user=userName)


# this is super weird, but somehow the clients try to resolve the domain
# names of the other clients
def updateClients():
    with open(clientFile, "r") as file:
        clients = file.read().split('\n')
        with mode_sudo():
            file_ensure(sshFile, owner=userName, group=userName)
            file_update('/etc/hosts', lambda _: text_ensure_line(_, *clients))
            if "master" in env.roles:
                with open(masterIPFile, "r") as mFile:
                    clients.append(mFile.read().strip())
                    file_write(configDir + '/slaves', '\n'.join(map(lambda x: x.split(" ")[0], clients)), group=userName, owner=userName)

    # we should reformat our index (this is dangerous)
    with mode_user(userName):
        hdfsConf()


def isMaster():
    return "master" in env.roles


def getMasterIP():
    if 'masterIP' not in env:
        with open(masterIPFile, "r") as file:
            env.masterIP = file.read()
    return env.masterIP


def cleanHdsfs():
    dir_remove(storeDir + "/hdfs/namenode/current", recursive=True)
    dir_remove(storeDir + "/hdfs/datanode/current", recursive=True)

def initDir():
    try:
        os.remove(clientFile)
        os.remove(masterIPFile)
        os.remove(keyFile)
    except OSError:
        pass
