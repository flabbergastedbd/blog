:date: 2019-05-14
:slug: linux-kernel-gdb-setup
:title: Quick linux kernel with gdb setup with little help from Linux distros
:category: Tools
:tags: reversing, tools
:image: /images/rinnegan_network.png

Requirements
============

When I was messing around with a kernel module I figured out a necessity to have a *debuggable
kernel with symbols*. It was a roller coaster ride from there to what I got working because of
multiple reasons that I will try to outline here.

* A working linux with shell access so that I can write and test my exploits.
* Minimal amount of steps to get it working.

Failed Attempts
===============

* Like many articles on internet suggest I started with compiling my own kernel and using busybox
  shell as rdinit. This is a good idea if you just want to debug kernel, if you have any complex
  module or need editors or anything of sort this is a very bad idea. Distro's kernels also have lots
  of patches to be applied before compiling them.
* Using busybox shell as init with a centos disk. This is again cuts down on init support etc. LKM
  that I was debugging was inserted using a systemd unit. Using busybox, I need to ensure all
  prerequisites to insmod the module.
* Using something like virtualbox gdb stub, this is too heavy and pointless.

Tips
====

* Just use vagrant to get minimal server image. Better to pick distro for which you have the installer
  package like rpm/deb/tar.xz.
* Stick to distro's init if your module or service trying to debug needs a full server emulation.
* Use qemu.
* Use something like gef or r2 for better debugging support. Vanilla gdb is never good for exploit dev.

Steps
=====

Let us get a working CentOS kernel with debug symbols in qemu with gdb.

* Use Vagrantfile to get up a simple vagrant box.

.. code-block:: bash

        vagrant init centos/7
        vagrant up

* SSH into the vm and do whatever permanant modifications (like installing packages etc..) are necessary.

.. code-block:: bash

        vagrant ssh

* This step is very distro dependent. Install debug kernel and edit grub to boot to it. Either using utilities
  or `direct download <http://debuginfo.centos.org/7/x86_64/>`_. Package managers tend to serve only latest ones.
  Get those debug packages onto host and extract them.

.. code-block:: bash

        # yum install kernel-debug

        This is a dirty way of doing it as changes will get wiped when grub mkconfig is run again.
        /etc/grub2.cfg can also be used.

        # vi /boot/grub2/grub.cfg

        $ uname -r
        3.10.0-957.12.1.el7.x86_64.debug

        # debuginfo-install --downloadonly 3.10.0-957.12.1.el7

* Use vagrant snapshots at this stage to keep it easy to revert if necessary.

* Stop all unnecessary systemd units to prevent them from starting. Make the kernel boot into console mode
  and enable kernel gdb. If using grub, add following to kernel parameters. Also kaslr to make the symbols
  make sense.

.. code-block:: bash

        console=ttyS0,115200 kgdboc=ttyS0,115200 nokaslr

* Start the kernel by pointing gdb to debug symbols. ``-nographic`` to start console only mode, ``-s`` to
  start gdb of qemu & ``-m`` to specify memory which we set as 3 gigs here.

.. code-block:: bash

        qemu-system-x86_64 -hda path_to_virtualmachine_disk.vmdk -nographic -s -m 3072

* If used vagrant, you can sign in using ``vagrant:vagrant``. Start gdb with relevant commands

.. code-block:: bash


