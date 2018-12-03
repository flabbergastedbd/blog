:date: 2018-12-02
:slug: rinnegan-walkthrough
:title: Rinnegan - A distributed tracer for blackbox systems
:category: Tools
:tags: reversing, tools
:image: https://raw.githubusercontent.com/google/honggfuzz/master/screenshot-honggfuzz-1.png

TLDR
====

Rinnegan is a tool that I wrote for greatly reducing my time in understanding and reversing
complex distributed systems. Source available at https://github.com/tunnelshade/rinnegan.

1. Background
=============

Imagine a setup of Chef which has a server, message queues, distributed database, configuration system and many more processes running on each of
servers that run core chef infrastructure. Now, finding bugs in Chef is a lot easier if you can understand how it works and sadly chef being a
product that sells, all it's inner workings are not publicly documented for us to read and understand.

So, I needed a way to visualize what components are running and what communications are happening between those components. Enter Rinnegan, named
after most powerul eyes from Naruto verse.

2. Idea
=======

Rinnegan uses Grafana dashboards for visualizing and influxdb for storing data. A collection of scripts help in deploying/managing a small agent on
all appliances of interest which help in collecting traces and do some basic tasks.


3. Walkthrough
==============

Let us use Rinnegan to start reversing HDFS Namenode and Datanode communications.

1. First we need to setup either docker or real instances of HDFS to use rinnegan. I highly recommend using docker instances as they tend to not
   have noisy system processes and traffic. Let us use `runtime-compose <https://github.com/flokkr/runtime-compose/tree/master/hdfs/viewfs>`_
   setup here.

.. code-block:: bash

   $ git clone https://github.com/flokkr/runtime-compose.git
   $ cd runtime-compose/hdfs/viewfs
   $ docker-compose up -d

   $ docker ps

   CONTAINER ID        IMAGE                             COMMAND                  CREATED             STATUS              PORTS                                                                NAMES
   5edb424b46eb        flokkr/hadoop:latest              "/usr/local/bin/dumb…"   11 seconds ago      Up 9 seconds        0.0.0.0:9870->9870/tcp                                               viewfs_nnx_1_425c196281b7
   05a31cf76a62        flokkr/hadoop:latest              "/usr/local/bin/dumb…"   11 seconds ago      Up 9 seconds                                                                             viewfs_datanodex_1_5179126eae48
   2d2f2c1ef143        flokkr/hadoop:latest              "/usr/local/bin/dumb…"   11 seconds ago      Up 9 seconds                                                                             viewfs_datanodey_1_1918ad4bf599
   2b64e94ac21a        flokkr/hadoop:latest              "/usr/local/bin/dumb…"   11 seconds ago      Up 9 seconds        0.0.0.0:9871->9870/tcp                                               viewfs_nny_1_db43ab680275

2. To start using rinnegan, we need to start rinnegan infrastructure

.. code-block:: bash

   $ git clone https://github.com/tunnelshade/rinnegan
   $ cd rinnegan/infrastructure
   $ make start

   $ docker ps

   CONTAINER ID        IMAGE                             COMMAND                  CREATED             STATUS              PORTS                                                                NAMES
   1173cd248fcd        grafana/grafana:5.2.4             "/run.sh"                21 minutes ago      Up 21 minutes       0.0.0.0:3000->3000/tcp                                               grafana
   524b5a9b9615        influxdb:1.6                      "/entrypoint.sh infl…"   21 minutes ago      Up 21 minutes       0.0.0.0:2003->2003/tcp, 0.0.0.0:8086->8086/tcp                       influxdb

3. Visit http://localhost:3000 in your browser and use default credentials ``admin:admin`` to login and go to rinnegan dashboard.
