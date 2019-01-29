:date: 2018-12-02
:slug: rinnegan-walkthrough
:title: Rinnegan - A distributed tracer for blackbox systems
:category: Tools
:tags: reversing, tools
:image: /images/rinnegan_network.png

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

Let us use Rinnegan to start reversing HDFS working.

1. To start using rinnegan, we need to start rinnegan infrastructure (Influx database & dashboard servers). All required steps are handled by
   a Makefile. Currently, you need `GOPATH <https://github.com/golang/go/wiki/SettingGOPATH>`_ setup for cross compilation of agent binary.

.. code-block:: bash

   $ go get https://github.com/tunnelshade/rinnegan
   $ cd $GOPATH/src/github.com/tunnelshade/rinnegan/infrastructure
   $ make start

   $ docker ps --format="{{.Names}}"

   grafana
   influxdb

2. Visit http://<localhostname>:3000 on your browser and use default credentials ``admin:admin`` to login. Navigate to rinnegan dashboard and you
   should see something like below.

.. image:: {static}/images/rinnegan_empty.png

3. We need a test hdfs setup to play around. I highly recommend using docker instances as they tend to not have noisy system processes and traffic.
   Let us use `runtime-compose <https://github.com/flokkr/runtime-compose/tree/master/hdfs/viewfs>`_ setup here.

.. code-block:: bash

   $ git clone https://github.com/flokkr/runtime-compose.git
   $ cd runtime-compose/hdfs/viewfs
   $ docker-compose up -d

   $ docker ps --format="{{.Names}}" | grep viewfs

   viewfs_datanodex_1
   viewfs_nny_1
   viewfs_nnx_1
   viewfs_datanodey_1

4. To do any operation on target containers/hosts, ``./bin/rinnegan.sh`` is the right utility. To use it, we need to fix two files present in
   ``samples/`` directory. ``hosts`` file is used to list one target per line. ``variables`` has some necessary environment variables set, fix them
   accordingly.

5. In current example, we are dealing with containers so hosts file should have names of all containers. Enable environment variable ``RINNEGAN_DOCKER``
   in variables to true and source it out.

.. code-block:: bash

   $ docker ps --format="{{.Names}}" > ./samples/hosts
   $ source ./samples/variables

6. Once sucessfully setup, running help should work.

.. code-block:: bash

   $ ./bin/rinnegan.sh --help

   Usage: rinnegan <host_regex> [agent|deploy|list|stop|wipe|exec]

	  <host_regex>  grep regex that will be applied to filter hosts

	     agent    Interact with agents deployed on targets
	     deploy   Deploy agents on to targets
	     list     List all active agents
	     stop     Stop all active agents
	     wipe     Remove any file leftovers on targets, run after stopping
	     exec     Run commands on targets directly, nothing fancy

7. Let us compile agent to be deployed. As all containers in this example are linux, just run ``make linux_agent``.
8. Time to deploy our agents and check if agent is running. Ignore any warnings of missing dependencies for modules.

.. code-block:: bash

   $ ./bin/rinnegan.sh "." deploy
   $ ./bin/rinnegan.sh "." list

9. Many times there is a necessity to run some commands on all the targets, this is easily possible in rinnegan. Let us see how to
   do that by installing procps on all containers.

.. image:: {static}/images/rinnegan_exec.png

10. Let us see, what all processes are run as part of a hdfs setup. Once command is run, checkout dashboard to see
    data over there.

.. code-block:: bash

   $ ./bin/rinnegan.sh "." agent module run ps

.. image:: {static}/images/rinnegan_ps.png


.. image:: {static}/images/rinnegan_ps_dashboard.png

11. Namenodes (nnx & nny) seem to have main process under pid 125. Let us trace it's network calls. For this we will be needing
    strace module, hence let us install it first only on nnx.

.. code-block:: bash

   $ ./bin/rinnegan.sh "nnx" exec apk add strace

12. Even after installing it, we do not see ``strace`` module. This way rinnegan is quite verbose in telling what is missing,
    which in this case is wrong *ptrace_scope* value. Let us start strace module as well.

.. code-block:: bash

   $ ./bin/rinnegan.sh "." exec sysctl -w kernel.yama.ptrace_scope=0
   $ ./bin/rinnegan.sh "nnx" agent module run strace 125 trace=desc

.. image:: {static}/images/rinnegan_strace.png

13. Dashboard should now be showing network traffic graphs and syscall traces in *Network panel*.

.. image:: {static}/images/rinnegan_strace_desc.png

.. image:: {static}/images/rinnegan_strace_content.png

14. It seems to be some kind of heartbeat, so let us stop this network tracer and find out which host is connecting to it.

.. code-block:: bash

   $ ./bin/rinnegan.sh "nnx" agent module list
   $ ./bin/rinnegan.sh "nnx" agent module stop strace_trace=desc_125

.. image:: {static}/images/rinnegan_strace_stop.png

15. Since this seems to be a server listening, let us look for ESTABLISHED connections of this process using netstat module.

.. code-block:: bash

   $ ./bin/rinnegan.sh "nnx" agent module run netstat 125

.. image:: {static}/images/rinnegan_netstat_run.png

16. Dashboard should be showing connections, from which we can deduce using **raddr** column that host *064c7310222b* is the one
    talking to our nnx.

.. image:: {static}/images/rinnegan_netstat.png

17. Stop netstat module and start network tracing **nnx** (pid: 125) & **064c7310222b** (pid: 68). Pids can be easily obtained from
    process panel. Pay attention that hostname is not always equal to container name that is used in targets list.

.. code-block:: bash

   $ ./bin/rinnegan.sh "nnx" agent module run strace 125 trace=desc
   $ ./bin/rinnegan.sh "nodex" agent module run strace 68 trace=desc

18. It is deducible that both hosts have a heartbeat kind of interaction in idle state. Filtering out on hosts should help remove
    remainder host's graphs. Best part is that dragging a rectangle on those graphs to include two spikes will modify timerange
    and you will only see syscall traces during that period.

.. image:: {static}/images/rinnegan_network.png

19. What next? Just enable tracers and try writing a file to hdfs to see how file blocks are written.
20. So, just pick any containerised blackbox distributed system and go about finding bugs by understading communications.

4. Capabilities
===============

What else is rinnegan capable of doing?

* Use iptables to easily redirect traffic between components to live tamper with traffic ``agent iptables --help``. A good http
  reverse proxy is ``mitmproxy``.

.. code-block:: bash

   $ ./bin/rinnegan.sh "nnx" agent iptables --help

* Use frida to run scripts like ssl-bypass for mitming ssl traffic. Rinnegan comes with cert check bypass script
  for openssl. Frida scripts are present in ``build/frida/``, adding a new script there requires you to redeploy
  or get that script to target and then just use script name without extension.

.. code-block:: bash

   $ ./bin/rinnegan.sh "nnx" exec apk add py-pip
   $ ./bin/rinnegan.sh "nnx" exec pip install frida-tools
   $ ./bin/rinnegan.sh "nnx" agent module run frida 125 ssl-bypass

5. Last word
============

Rinnegan is a very experimental software which gets feature as and when I need them, but it has been super helpful in reversing
some complex blackbox systems. It was built to solve my constant frustration of having to check processes, trace them, redirect
traffic and tamper with those.

If something seems to be not working

* Wipe agent from particular target.
* Kill rinnegan related processes (HINT: Use exec).
* Redeploy agent and resume.
