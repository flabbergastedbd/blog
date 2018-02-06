:date: 2018-02-06
:slug: afl-internals-qemu-instrumentation
:title: Internals of AFL fuzzer - QEMU Instrumentation
:category: Tools
:tags: fuzzing, reversing

Introduction
============

If you need an introduction to `AFL <http://lcamtuf.coredump.cx/afl/>`_, you have probably missed out a lot in the instrumented binary fuzzing saga
for the past couple of years. **afl-fuzz**\ (fuzzer part of this toolset) is extremely fast, easy to use and requires minimal configuration.
Technical details of AFL are available `here <http://lcamtuf.coredump.cx/afl/technical_details.txt>`_. All this awesomeness was written in C, a
language that I almost never used. So I wanted to try and understand the implementation i.e How ideas were translated to code in AFL.

Before proceeding further, it is recommended to read through `afl compile time instrumentation <{filename}afl-internals-compile-time-instrumentation.rst>`_.
Now, what about the black box binaries for which source code is unavailable?? Instrumentation was used to

- Trace the execution flow of basic blocks for the specificied fuzzy input.
- Save time by fuzzing in a `forkserver model <https://lcamtuf.blogspot.in/2014/10/fuzzing-binaries-without-execve.html>`_.

One way is to parse the given binary and rewrite it along with the instrumentation (afl-dyninst).

QEMU
====

`QEMU <https://www.qemu.org/>`_ is a process emulator that lets you run different architectures on a single machine by doing dynamic translation. Read `qemu
binary translation <https://www.slideshare.net/RampantJeff/qemu-binary-translation>`_. The important steps are

- Basic blocks in the target binary are translated into host architecture. The translated blocks are
    - known as *TB*.
    - cached in *T*\ ranslated *B*\ lock *C*\ ache (TBC).
    - translated only when the instruction pointer jumps into it.

- Execution flow

.. image:: https://image.slidesharecdn.com/qemu-binarytranslation-140930222818-phpapp02/95/qemu-binary-translation-15-638.jpg


1. Idea
-------

Consider a sample program which determines a command line parameter to be even or odd.

.. code-block:: c

        #include <stdio.h>
        #include <stdlib.h>
        #include <time.h>

        int main(int arc, char *argv[]) {
                ((atoi(argv[1]) % 2) == 1) ? printf("Odd") : printf("Even");
                return 0;
        }


Coverage guided fuzzing requires the fuzzer to be aware of execution flow in the target in response to a certain input. One way to achieve it is to
modify the source code in a way to trace the flow. Somewhat like

.. code-block:: c

        #include <stdio.h>
        #include <stdlib.h>
        #include <time.h>

        int main(int arc, char *argv[]) {
                notifyFuzzer("main starting")
                if ((atoi(argv[1]) % 2) == 1) {
                        notifyFuzzer("if condition taken")
                        printf("Odd");
                } else {
                        notifyFuzzer("else condition taken")
                        printf("Even");
                }
                return 0;
        }

Question remains - *How to instrument super huge code base in a language agnostic and collision resistant manner?*

  HINT: Compilers (language -> assembly), assembler (assembly -> object code), linker (object code -> executable/library)

Assembler is a good place to instrument the basic blocks. For example, `gcc <https://gcc.gnu.org/>`_ by default uses `GNU as <https://en.wikipedia.org/wiki/GNU_Assembler>`_
assembler. `afl-gcc <https://github.com/mcarpenter/afl/blob/be2c066ef0939ea2b49435535ed614c37906ba30/afl-gcc.c>`_ is a wrapper around gcc which uses
`afl-as <https://github.com/mcarpenter/afl/blob/be2c066ef0939ea2b49435535ed614c37906ba30/afl-as.c>`_ by symlinking *afl-as* as *as* and adding the directory to compiler
search path via ``-B``.

2. Coverage Measurements
------------------------

Please go through **Coverage measurements** section of the technical paper for an indepth understanding of it. A quick recap for the enlightened ones, AFL assigns a random
compile time constant to each basic block and uses a 64kB array to trace the execution flow with the help of following logic.

.. code-block:: c

        cur_location = <COMPILE_TIME_RANDOM>;
        shared_mem[cur_location ^ prev_location]++;
        prev_location = cur_location >> 1;

3. Communication
----------------

- AFL uses forkserver model to fuzz a program. For more info on the forkserver model of fuzzing, check `this <https://lcamtuf.blogspot.in/2014/10/fuzzing-binaries-without-execve.html>`_.
- Instance of the instrumented binary will be used as a forkserver which will communicate with the fuzzer process via fds 198 (control queue) & 199 (status queue).
- Clones of this forkserver instance are used to run the testcases. So, techically the actual fuzzy input execution happens in grandchildren process of the fuzzer.
- The execution trace from the target is available via shared memory (shm) to the fuzzer process.

4. Implementation
-----------------

**afl-as** `parses <https://github.com/mcarpenter/afl/blob/be2c066ef0939ea2b49435535ed614c37906ba30/afl-as.c#L254>`_ the assembly file and adds

- `a trampoline <https://github.com/mcarpenter/afl/blob/9185f39b38b84bfdfba9824e70d3e8480472af76/afl-as.h#L130>`_ at places where flow needs to be recorded. Each trampoline
  written has a unique constant hardcoded in it, which is used for tracing the flow between different blocks. That constant is loaded into [re]cx and **__afl_maybe_log**
  ion is called. AFL generally places a trampoline at the beginning of main to create the forkserver.

        .. code-block:: assembly

                lea rsp, qword rsp - 0x98
                mov qword [rsp], rdx
                mov qword [arg_8h], rcx
                mov qword [arg_10h], rax
                mov rcx, 0xcb0
                call loc.__afl_maybe_log
                mov rax, qword [arg_10h]
                mov rcx, qword [arg_8h]
                mov rdx, qword [rsp]
                lea rsp, qword rsp + 0x98

- `a main payload <https://github.com/mcarpenter/afl/blob/9185f39b38b84bfdfba9824e70d3e8480472af76/afl-as.h#L381>`_ which consists of multiple __afl code locations like
  *__afl_maybe_log* and other variable declarations that will be used by those functions. In an instrumented binary you can find the following afl related symbols, all NOTYPE
  ones are basically assembly code locations for jumping to and OBJECT symbols are for variable data.

        ========= ========== ======================= ===============================================================================================
           Type      Bind       Name                        Usage
        ========= ========== ======================= ===============================================================================================
          NOTYPE     LOCAL    __afl_maybe_log()         The only function called from trampoline
                                                        - (__afl_area_ptr == 0) __afl_setup() : __afl_store()
          NOTYPE     LOCAL    __afl_setup()             - if __afl_setup_failure != 0: __afl_return()
                                                        - __afl_global_area_ptr == 0 ? __afl_setup_first() : __afl_store()
          NOTYPE     LOCAL    __afl_setup_first()       One time setup inside the target process
                                                        - Get shm id from env var __AFL_SHM_ID
                                                        - Map the shared memory and store the location in __afl_area_ptr & __afl_global_area_ptr
                                                        - __afl_forkserver()
          NOTYPE     LOCAL    __afl_store()             - shared_mem[cur_loc ^ prev_loc]++; prev_loc = cur_loc >> 1;
          NOTYPE     LOCAL    __afl_die()               Call exit()
          NOTYPE     LOCAL    __afl_forkserver()        Write 4 bytes to fd 199 and __afl_fork_wait_loop()
          NOTYPE     LOCAL    __afl_fork_wait_loop()    - Wait for 4 bytes on fd 198 and then clone the current process
                                                        - In child process, __afl_fork_resume()
                                                        - In parent
                                                            - Store child pid to __afl_fork_pid
                                                            - Write it to fd 199 and call waitpid which will write child exit status to __afl_temp
                                                            - Write child exit status in __afl_tempt to fd 199.
                                                            - __afl_fork_wait_loop()
          NOTYPE     LOCAL    __afl_fork_resume()       Closes the fds 198 & 199 (fuzzer <-> forkserver comm) & resumes with execution
          NOTYPE     LOCAL    __afl_setup_abort()       Increment __afl_setup_failure and __afl_return()
          NOTYPE     LOCAL    __afl_return()            Simple return
          OBJECT     GLOBAL   __afl_global_area_ptr     Global ptr to shared memory
          OBJECT     LOCAL    __afl_area_ptr            Ptr to shared memory
          OBJECT     LOCAL    __afl_fork_pid            Cloned pid variable
          OBJECT     LOCAL    __afl_prev_loc            Previous location variable, used to update traces in shared memory
          OBJECT     LOCAL    __afl_setup_failure       Counter to setup failures
          OBJECT     LOCAL    __afl_temp                Temp varible for different purposes
        ========= ========== ======================= ===============================================================================================

5. Example
----------

Try compiling the above c code with afl-gcc and have a look at the decompiled main(). The easiest way to picturise is to use graph mode of your
disassembler. The intention is to show the injection of trampolines in all basic blocks.

.. code-block:: terminal

                                              .------------------------------------------------------------------.
                                              | [0x810] ;[gd]                                                    |
                                              |   ; section 13 va=0x00000810 pa=0x00000810 sz=1730 vsz=1730 rwx= |
                                              |   ;-- main:                                                      |
                                              |   ;-- section_end..plt:                                          |
                                              |   ;-- section..text:                                             |
                                              | (fcn) sym.main 311                                               |
                                              | lea rsp, qword rsp - 0x98; test.c:5 int main(int arc, char *argv |
                                              | mov qword [rsp], rdx; .//:1347                                   |
                                              | mov qword [arg_8h], rcx                                          |
                                              | mov qword [arg_10h], rax                                         |
                                              | mov rcx, 0xcb0                                                   |
                                              | call loc.__afl_maybe_log;[ga]                                    |
                                              | mov rax, qword [arg_10h]                                         |
                                              | mov rcx, qword [arg_8h]                                          |
                                              | mov rdx, qword [rsp]                                             |
                                              | lea rsp, qword rsp + 0x98                                        |
                                              | ...                                                              |
                                              `------------------------------------------------------------------'
                                                      | |
                                                      | '-------------------------------.
              .---------------------------------------'                                 |
              |                                                                         |
              |                                                                         |
      .----------------------------------------------------------------------.    .-----------------------------------------------------------------------.
      | nop dword [rax]                                                      |    |      ; JMP XREF from 0x0000086b (sym.main)                            |
      | lea rsp, qword rsp - 0x98                                            |    | nop                                                                   |
      | mov qword [rsp], rdx                                                 |    | lea rsp, qword rsp - 0x98; test.c:6  ((atoi(argv[1]) % 2) == 1) ? pri |
      | mov qword [arg_8h], rcx                                              |    | mov qword [rsp], rdx                                                  |
      | mov qword [arg_10h], rax                                             |    | mov qword [arg_8h], rcx                                               |
      | mov rcx, 0x7fee                                                      |    | mov qword [arg_10h], rax                                              |
      | call loc.__afl_maybe_log;[ga]                                        |    | mov rcx, 0xa6de                                                       |
      | ; [0x10:8]=0x1003e0003                                               |    | call loc.__afl_maybe_log;[ga]                                         |
      | mov rax, qword [arg_10h]                                             |    | ; [0x10:8]=0x1003e0003                                                |
      | ; [0x8:8]=0                                                          |    | mov rax, qword [arg_10h]                                              |
      | ...                                                                  |    | ; [0x8:8]=0                                                           |
      `----------------------------------------------------------------------'    | ...                                                                   |
                                                                                  `-----------------------------------------------------------------------'
