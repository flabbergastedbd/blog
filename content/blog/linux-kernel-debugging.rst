:date: 2019-05-14
:slug: linux-kernel-gdb-setup
:title: Quick linux kernel with gdb setup with little help from Linux distros
:category: Tools
:tags: reversing, tools
:image: /images/kernel_debugging_gdb.png

Intro
=====

When messing around with a linux kernel module I needed to have a **debuggable kernel with symbols**.
It was a roller coaster ride from there to what I got working because of multiple reasons that I
will try to outline here.

Requirements
============

* A working linux kernel with shell access so that I can write and test my exploits.
* Minimal amount of steps to get it working.

Failed Attempts
===============

* Compiling own kernel with debug symbols and using busybox shell as rdinit is a good idea if you just
  want to debug kernel. If you have any complex module this is a very bad idea.
* Distro's kernels also have lots of patches to be applied before compiling them which makes it daunting
  to do it seperately without the respective package manager.
* Using busybox shell as `init`_ with a centos disk. This again cuts down on init support etc. Module
  that I was debugging needed insertion using a systemd unit. If using busybox, I need to ensure all
  prerequisites to insmod the module which is a waste of time.
* Using something like `virtualbox gdb`_ stub, this is too heavy and pointless on a linux host.

Tips
====

* Just use `vagrant`_ to get minimal server image. Better to pick distro for which you have the installer
  package like rpm/deb/tar.xz.
* Stick to distro's `init`_ if your module or service needs a full distro like emulation to work.
* Use `qemu`_ on a linux machine with kvm enabled, it sucks big time on osx though.
* Use something like `gef`_ or `radare2`_ for better debugging support. Vanilla gdb is never good for exploit dev.
* Ensure that some symbol like ``start_kernel`` has same address (/proc/kallsyms) in booted kernel as your `vmlinux`_ file.
* There are plenty of `gdb macros <https://www.kernel.org/doc/html/v4.10/dev-tools/gdb-kernel-debugging.html>`_ for getting
  around kernel structures, use them. Be aware that kernel structures change with versions.

Steps
=====

Let us run a working CentOS 7 with debug symbols in qemu and debug with gdb.

1. Start up a simple vagrant box with the minimal centos image.

        .. code-block:: bash

                $ vagrant init centos/7
                $ vagrant up

2. SSH into the vm and do whatever permanant modifications (like installing packages etc..) are necessary.

        .. code-block:: bash

                $ vagrant ssh

3. This step is very distro dependent. Download debug info for running kernel either using package manager
   or `direct download <http://debuginfo.centos.org/7/x86_64/>`_. Get those debug packages onto host and extract them.

        .. code-block:: bash

                $ uname -r
                3.10.0-957.12.1.el7.x86_64

                $ debuginfo-install --downloadonly 3.10.0-957.12.1.el7

4. Remove all unnecessary systemd units that you don't need. Make the kernel boot into console mode, disable kaslr
   and enable `kgdb`_ by adding following line to kernel parameters.

        .. code-block:: bash

                # Add this to default parameters in /etc/default/grub
                # console=ttyS0,115200 kgdboc=ttyS0,115200 nokaslr

                $ grub2-mkconfig -o /boot/grub2/grub.cfg

5. Use vagrant snapshots at this stage to keep it easy to revert if necessary.

6. Start the kernel with qemu.
        * ``-enable-kvm`` to use linux kvm
        * ``-hda`` to specify hd0 for vm
        * ``-nographic`` to start console only mode of qemu
        * ``-s`` to start gdbserver of qemu on :1234 (check help)
        * ``-m`` to specify memory which we set as 3 gigs here.

        .. code-block:: bash

                $ qemu-system-x86_64 -enable-kvm -hda path_to_virtualmachine_disk.vmdk -nographic -s -m 3072

7. On host, from the directory where debug rpms were extracted let us start gdb and point it to source

        .. code-block:: bash

                $ cat kerinit.gdb

                dir usr/src/debug/kernel-3.10.0-957.12.1.el7/linux-3.10.0-957.12.1.el7.x86_64
                target remote :1234

                $ gdb -x kerninit.gdb usr/lib/debug/lib/modules/3.10.0-957.12.1.el7.x86_64/vmlinux


Following is a breakpoint hit at ``do_sys_open``

.. image:: {static}/images/kernel_debugging_gdb.png

.. _gef: https://github.com/hugsy/gef
.. _radare2: https://github.com/radare/radare2
.. _qemu: https://www.qemu.org/
.. _vagrant: https://www.vagrantup.com/
.. _init: https://stackoverflow.com/questions/20744200/how-is-the-init-process-started-in-the-linux-kernel
.. _virtualbox gdb: http://sysprogs.com/VBoxGDB/tutorial/
.. _kgdb: https://en.wikipedia.org/wiki/KGDB
.. _vmlinux: https://en.wikipedia.org/wiki/Vmlinux
