:date: 2017-11-12
:slug: playing-with-python-pex
:title: Playing with python PEX files
:category: Python
:tags: tricks, info, python, reversing

Introduction
------------

Recently I have been coming across lots of **P**\ ython **EX**\ ecutables. This seems to be a popular way of distributing
python programs along with their dependencies. All that is necessary is a compatible python runtime. A very quick and a bit
outdated `WTF is PEX? <http://www.youtube.com/watch?v=NmpnGhRwsu0>`_. In most cases the dependencies of a python program are packaged
into the pex for reasons stated above.

Objectives
----------

I had two very rigid objectives when dealing with pex files

* See the source code of the main package or script along with its dependencies.
* Have the ability to mess around with the existing code and run it without having to setup requirements etc..

Playground
----------

**coverage** console script is something that I frequently use, so let us create a coverage clone and understand the unpacking of a pex.
Create a virtualenv and install pex in it. To create a pex that works like coverage::

        pex pex coverage -c coverage -o coverage.pex

`pex` & `coverage` are dependencies to be included, `-c` states the console script to be used as entrypoint and `-o` states the output file name.
The craziest part is this command will work even if you do not have coverage installed, that is because pex gets it and packages it. Now try::

        ./coverage.pex --help

Fancy right.

Unpacking
---------

PEX files are zip files with a python hashbang at the beginning. Don't believe me??

.. code-block:: console

        00000000  23 21 2f 75 73 72 2f 62  69 6e 2f 65 6e 76 20 70  |#!/usr/bin/env p|
        00000010  79 74 68 6f 6e 32 2e 37  0a 50 4b 03 04 14 00 00  |ython2.7.PK.....|
        00000020  00 08 00 55 82 6c 4b 7b  66 ca fb 78 00 00 00 83  |...U.lK{f..x....|
        00000030  00 00 00 1b 00 00 00 2e  62 6f 6f 74 73 74 72 61  |........bootstra|
        00000040

So, let us unzip the pex and see the file structure (Some files and folders are removed for brevity)

.. code-block:: console

        ├── .bootstrap
        │   ├── _pex
        │   └── pkg_resources
        ├── coverage.pex
        ├── .deps
        │   ├── coverage-4.4.2-cp27-cp27mu-linux_x86_64.whl
        │   │   ├── coverage
        │   │   └── coverage-4.4.2.dist-info
        │   ├── pex-1.2.13-py2.py3-none-any.whl
        │   │   ├── pex
        │   │   └── pex-1.2.13.dist-info
        │   ├── setuptools-33.1.1-py2.py3-none-any.whl
        │   │   ├── easy_install.py
        │   │   ├── pkg_resources
        │   │   ├── setuptools
        │   │   └── setuptools-33.1.1.dist-info
        │   └── wheel-0.29.0-py2.py3-none-any.whl
        │       ├── wheel
        │       └── wheel-0.29.0.dist-info
        ├── hello.py
        ├── __main__.py
        └─ PEX-INFO

So, it can be easily understood that

==============  ===========================================================================
   dir/file                                   contents
==============  ===========================================================================
 .bootstrap       Bootstrapping scripts to setup environment and launch the entrypoint.
 .deps            whls of dependencies.
 PEX-INFO         Name says so.
 __main__.py      Entrypoint for the archive as specified by python spec.
==============  ===========================================================================

**PEX-INFO** looks like

.. code-block:: json

        {
          "always_write_cache": false,
          "build_properties": {
            "class": "CPython",
            "platform": "linux-x86_64",
            "version": [
              2,
              7,
              12
            ]
          },
          "code_hash": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
          "distributions": {
            "coverage-4.4.2-cp27-cp27mu-linux_x86_64.whl": "bfb4e061b724fe9a50c2cf048c8d35d10a664728",
            "pex-1.2.13-py2.py3-none-any.whl": "6bfeb70d4c4280954ddc331c1f3a49cad35a567d",
            "setuptools-33.1.1-py2.py3-none-any.whl": "d5c7021b0a2ca18f60b7dd7a5b9ffebcb789d43b",
            "wheel-0.29.0-py2.py3-none-any.whl": "c6b9e44d951cdabf4dc67205b0f30184a1b602bb"
          },
          "entry_point": "coverage.cmdline:main",
          "ignore_errors": false,
          "inherit_path": false,
          "pex_path": null,
          "requirements": [
            "wheel==0.29.0",
            "pex==1.2.13",
            "setuptools==33.1.1",
            "coverage==4.4.2"
          ],
          "zip_safe": true
        }

and **__main__.py** like this

.. code-block:: python
        :linenos: table

        import os
        import sys

        __entry_point__ = None
        if '__file__' in locals() and __file__ is not None:
          __entry_point__ = os.path.dirname(__file__)
        elif '__loader__' in locals():
          from zipimport import zipimporter
          from pkgutil import ImpLoader
          if hasattr(__loader__, 'archive'):
            __entry_point__ = __loader__.archive
          elif isinstance(__loader__, ImpLoader):
            __entry_point__ = os.path.dirname(__loader__.get_filename())

        if __entry_point__ is None:
          sys.stderr.write('Could not launch python executable!\n')
          sys.exit(2)

        sys.path[0] = os.path.abspath(sys.path[0])
        sys.path.insert(0, os.path.abspath(os.path.join(__entry_point__, '.bootstrap')))

        from _pex.pex_bootstrapper import bootstrap_pex
        bootstrap_pex(__entry_point__)

If you try running the **__main__** file directly, a error will popup.

Executing
---------

The last two lines of the main script when modified to launch an environment of the executable, the console script can
be invoked as necessary. i.e

.. code-block:: python

        """
        from _pex.pex_bootstrapper import bootstrap_pex
        bootstrap_pex(__entry_point__)
        """

        # Call bootstrap_pex_env to set up the required environment
        from _pex.pex_bootstrapper import bootstrap_pex_env
        bootstrap_pex_env(".")

        # Call the entry point as you please. In case of coverage entry
        # point is coverage.cmdline:main()
        from coverage.cmdline import main
        main()

With the modified file, try

.. code-block:: console

        $ python __main__.py --help

        Coverage.py, version 4.4.2 with C extension
        Measure, collect, and report on code coverage in Python programs.

        usage: __main__.py <command> [options] [args]

        Commands:
            annotate    Annotate source files with execution information.
            combine     Combine a number of data files.
            erase       Erase previously collected coverage data.
            help        Get help on using coverage.py.
            html        Create an HTML report.
            report      Report coverage stats on modules.
            run         Run a Python program and measure code execution.
            xml         Create an XML report of coverage results.

        Use "__main__.py help <command>" for detailed help on any command.
        For full documentation, see https://coverage.readthedocs.io

Now, we are free to edit the main program or any dependencies in **.deps** as we please
and test it. (Try removing \*.pyc if your changes are not reflected)

Recap
-----

1. Unzip the pex.
2. Edit the ``__main__.py`` to call ``bootstrap_pex_env(".")``.
3. Call the whichever entrypoint you wish.

.. warning:: Make sure that the python version you are trying to run the ``__main__.py`` is compatible according to ``PEX-INFO``.
