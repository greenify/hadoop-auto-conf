#!/bin/bash

hadoopFile="hadoop-2.5.2"
installDir="/opt/hadoop"
storeDir="/opt/hadoop_store"
masterName="spark-master"
masterIP="172.42.0.19"
isMaster=0

masterKey="ssh-dss AAAAB3NzaC1kc3MAAACBAPqoZ+RwByLbuQl57EhUlEDIZhQDiqYfiwAX5IDJH9toTYCiUb0bieejXuOBGhyQmLLdQPYdzjN5gLTsTxHmLBEyDglaXEYP5l25brvdMrPi3ywaxke5PNBJplBMhJmQghvaYUktDJJaewseeVOCYf4TMIUjAWgdeg68NHbmAikNAAAAFQC8si76oiHb8XVSAYwHjdWPx/tDlQAAAIA7SGf0PfOCkYhinxFu+8lmkjiczie05CUQCXMGPIb2wvEldpNQJr7UoJui8aNtm7xScjFvCLIWUjZSDGGLVBGKuJgZivAGUm3OkmXmj8qrvBJPMb+NoYvkgh47gMyY8R+JeKTzU4Yvp2vDHxT4W6qEiWiF1a8bbaKMTTnj8PGRVgAAAIEAyy3Wb6dLwoyKYy7KOoON9qwq30mrfmfS85VK9bsNPjIPT/6hOZ0lpkFnFASXcVHlfViakpqFAPsxnOi8u3ninydO9oIC9oY2zDfIWuFj3+9AXG9h7SgJrcDlfVQigrkyAVQaY526B2T61dzZqDKoYP/NKtCGjyV63/q03GthYKI= ubuntu@master"

# java
export JAVA_HOME="/usr/lib/jvm/java-7-openjdk-amd64"

# script.sh 1 -> sets the master flag
if [ $# -ne 0 ] ; then
	isMaster=1
	echo "Welcome Master."
fi

if [ ! -f $hadoopFile".tar.gz" ] ; then
	# install java
	echo 'Y' | sudo apt-get install openjdk-7-jdk

	cd ~
	wget "http://apache.mirror.iphh.net/hadoop/common/$hadoopFile/$hadoopFile"".tar.gz"

	echo "unpacking hadoop. takes a bit"
	tar xfz $hadoopFile".tar.gz"
	
	# cleanup
	sudo rm -rf "$installDir" "$storeDir"
	sudo mkdir -p "$storeDir"

	# move and change permission
	sudo mv $hadoopFile "$installDir"
	sudo chown ubuntu:ubuntu "$installDir" "$storeDir"

	# ssh setup
	echo "generating new ssh key"
	echo "..."
	echo -e  '\n'|ssh-keygen -q -t rsa -N "" -P ''  > /dev/null 2>&1
	cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

	echo $masterKey >> ~/.ssh/authorized_keys 
else
	echo "existing hadoop install found"
fi

#add to the hosts config
if [[ ! $( grep "$masterName" /etc/hosts ) ]] ; then
	echo "configured master in the /etc/hosts"
	sudo sh -c "printf '# hadoop master config\n$masterIP $masterName\n' >> /etc/hosts"
fi

#add own hostname
hostName=$(hostname)
if [[ ! $( grep "$hostName" /etc/hosts ) ]] ; then
	ipAdress=$(ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
	sudo sh -c "printf '# own hostname\n$ipAdress $hostName\n' >> /etc/hosts"
fi

# add some handy paths
if [[ ! $( grep "HADOOP_INSTALL" ~/.bashrc) ]] ; then
printf "export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64 \n\
export HADOOP_INSTALL=$installDir \n\
export PATH=\$PATH:\$HADOOP_INSTALL/bin \n\
export PATH=\$PATH:\$HADOOP_INSTALL/sbin \n\
export HADOOP_MAPRED_HOME=\$HADOOP_INSTALL \n\
export HADOOP_COMMON_HOME=\$HADOOP_INSTALL \n\
export HADOOP_HDFS_HOME=\$HADOOP_INSTALL \n\
export YARN_HOME=\$HADOOP_INSTALL \n\
export HADOOP_COMMON_LIB_NATIVE_DIR=\$HADOOP_INSTALL/lib/native \n\
export HADOOP_OPTS='-Djava.library.path=\$HADOOP_INSTALL/lib -Djava.net.preferIPv4Stack=true '\n" >> ~/.bashrc
else
	echo "incremental install"
fi

source ~/.bashrc

# update java home
sed -e "s!\${JAVA_HOME}!'$JAVA_HOME'!" -i "$installDir/etc/hadoop/hadoop-env.sh"

siteConfig="<property> \n \
	<name>fs.default.name</name> \n \
	<value>hdfs://$masterName:9000</value> \n\
</property>"


# update sites 
perl -0pe  "s!(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)!$siteConfig!m" -i "$installDir/etc/hadoop/core-site.xml"



# yarns
yarnConfig="<property> \n\
   <name>yarn.nodemanager.aux-services</name> \n\
   <value>mapreduce_shuffle</value> \n\
</property> \n\
  <property>
       <name>yarn.resourcemanager.hostname</name>
       <value>$masterName</value>
       <description>Master resource manager</description>
   </property>
<property> \n\
   <name>yarn.nodemanager.aux-services.mapreduce.shuffle.class</name> \n\
   <value>org.apache.hadoop.mapred.ShuffleHandler</value> \n\
</property>"

perl -0pe  "s!(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)!$yarnConfig!m" -i "$installDir/etc/hadoop/yarn-site.xml"


# mapred

cp "$installDir"/etc/hadoop/mapred-site.xml.template "$installDir"/etc/hadoop/mapred-site.xml

mapredConfig="<property> \n\
   <name>mapreduce.framework.name</name> \n\
   <value>yarn</value> \n\
</property>"

perl -0pe  "s!(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)!$mapredConfig!m" -i "$installDir"/etc/hadoop/mapred-site.xml


# hdfs sites
mkdir -p "$storeDir"/hdfs/datanode

# config hdfs

hdfsConfig="<property> \n\
   <name>dfs.replication</name> \n\
   <value>1</value> \n\
 </property> \n\
 <property> \n\
   <name>dfs.datanode.data.dir</name> \n\
   <value>file:$storeDir/hdfs/datanode</value> \n\
 </property> \n";

# only the master should have a namenode
if [ $isMaster -eq 1 ] ; then

echo "real namenode"

hdfsConfig=$hdfsConfig"<property> \n\
   <name>dfs.namenode.name.dir</name> \n\
   <value>file:$storeDir/hdfs/namenode</value> \n\
 </property>"

mkdir -p "$storeDir"/hdfs/namenode
fi

perl -0pe  "s!(?<=<configuration>)(.|\n)*(?=\n<\/configuration>)!$hdfsConfig!m" -i "$installDir/etc/hadoop/hdfs-site.xml"


# format

# the master automatically runs these scripts on client nodes
if [ $isMaster -eq 1 ] ; then

# hdfs

"$installDir/bin/hdfs" $hdfs namenode -format

# rock & roal

if [[ ! $(pgrep -f nodemanager) ]] ; then

"$installDir"/sbin/start-dfs.sh

else
	echo "DFS is already running."
fi

# start other stuff
if [[ ! $(pgrep -f yarn ) ]] ; then

"$installDir"/sbin/start-yarn.sh
else
	echo "Yarn is already running."

fi

fi
echo "don't forget to run: source ~/.bashrc"
