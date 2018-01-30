:date: 2018-01-31
:slug: afl-internals-compile-time-instrumentation
:title: Internals of AFL fuzzer - Compile Time Instrumentation
:category: C
:tags: fuzzing

Introduction
============

If you need an introduction to `AFL <http://lcamtuf.coredump.cx/afl/>`_, you have probably missed out a lot in the instrumented binary fuzzing saga
for the past couple of years. **afl-fuzz**\ (fuzzer part of this toolset) is extremely fast, easy to use and requires minimal configuration.
Technical details of AFL are available `here <http://lcamtuf.coredump.cx/afl/technical_details.txt>`_. All this awesomeness was written in C, a
language that I almost never used. So I wanted to try and understand the implementation i.e How ideas were translated to code in AFL.

Instrumentation
===============

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

Question remains - *How to instrument super huge code base in a language agnostic and collision resistant manner?*.::

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

The following snippet is of instrumented binary of above c code. The intention is to show the injection of trampolines.

.. code-block:: assembly

                    ;-- main:
                    ;-- section_end..plt:
                    ;-- section..text:
                    ;-- rip:
        / (fcn) sym.main 311
        |           0x00000810      488da42468ff.  lea rsp, qword rsp - 0x98   ; test.c:5 int main(int arc, char *argv[]) { ; section 13 va=0x00000810 pa=0x00000810 sz=1730 vsz=1730 rwx=--r-x .text
        |           0x00000818      48891424       mov qword [rsp], rdx        ; .//:1347
        |           0x0000081c      48894c2408     mov qword [arg_8h], rcx
        |           0x00000821      4889442410     mov qword [arg_10h], rax
        |           0x00000826      48c7c1b00c00.  mov rcx, 0xcb0
        |           0x0000082d      e82e020000     call loc.__afl_maybe_log
        |           0x00000832      488b442410     mov rax, qword [arg_10h]    ; [0x10:8]=0x1003e0003
        |           0x00000837      488b4c2408     mov rcx, qword [arg_8h]     ; [0x8:8]=0
        |           0x0000083c      488b1424       mov rdx, qword [rsp]
        |           0x00000840      488da4249800.  lea rsp, qword rsp + 0x98
        |           0x00000848      4883ec08       sub rsp, 8
        |           0x0000084c      488b7e08       mov rdi, qword [rsi + 8]    ; stdlib.h:248   return (int) strtol (__nptr, (char **) NULL, 10); ; [0x8:8]=0
        |           0x00000850      ba0a000000     mov edx, 0xa
        |           0x00000855      31f6           xor esi, esi
        |           0x00000857      e864ffffff     call sym.imp.strtol         ; long strtol(const char *str, char**endptr, int base)
        |           0x0000085c      89c2           mov edx, eax                ; test.c:6  ((atoi(argv[1]) % 2) == 1) ? printf("Odd") : printf("Even");
        |           0x0000085e      c1ea1f         shr edx, 0x1f
        |           0x00000861      01d0           add eax, edx
        |           0x00000863      83e001         and eax, 1
        |           0x00000866      29d0           sub eax, edx
        |           0x00000868      83f801         cmp eax, 1
        |       ,=< 0x0000086b      0f848a000000   je 0x8fb
        |       |   0x00000871      0f1f00         nop dword [rax]
        |       |   0x00000874      488da42468ff.  lea rsp, qword rsp - 0x98
        |       |   0x0000087c      48891424       mov qword [rsp], rdx
        |       |   0x00000880      48894c2408     mov qword [arg_8h], rcx
        |       |   0x00000885      4889442410     mov qword [arg_10h], rax
        |       |   0x0000088a      48c7c1ee7f00.  mov rcx, 0x7fee
        |       |   0x00000891      e8ca010000     call loc.__afl_maybe_log
        |       |   0x00000896      488b442410     mov rax, qword [arg_10h]    ; [0x10:8]=0x1003e0003
        |       |   0x0000089b      488b4c2408     mov rcx, qword [arg_8h]     ; [0x8:8]=0
        |       |   0x000008a0      488b1424       mov rdx, qword [rsp]
        |       |   0x000008a4      488da4249800.  lea rsp, qword rsp + 0x98
        |       |   0x000008ac      488d3d350600.  lea rdi, qword str.Even     ; 0xee8 ; "Even"
        |       |   0x000008b3      31c0           xor eax, eax
        |       |   0x000008b5      e8d6feffff     call sym.imp.printf         ; int printf(const char *format)
        |       |      ; JMP XREF from 0x00000942 (sym.main)
        |      .--> 0x000008ba      6690           nop
        |      :|   0x000008bc      488da42468ff.  lea rsp, qword rsp - 0x98   ; test.c:8 }
        |      :|   0x000008c4      48891424       mov qword [rsp], rdx
        |      :|   0x000008c8      48894c2408     mov qword [arg_8h], rcx
        |      :|   0x000008cd      4889442410     mov qword [arg_10h], rax
        |      :|   0x000008d2      48c7c14f6300.  mov rcx, 0x634f
        |      :|   0x000008d9      e882010000     call loc.__afl_maybe_log
        |      :|   0x000008de      488b442410     mov rax, qword [arg_10h]    ; [0x10:8]=0x1003e0003
        |      :|   0x000008e3      488b4c2408     mov rcx, qword [arg_8h]     ; [0x8:8]=0
        |      :|   0x000008e8      488b1424       mov rdx, qword [rsp]
        |      :|   0x000008ec      488da4249800.  lea rsp, qword rsp + 0x98
        |      :|   0x000008f4      31c0           xor eax, eax
        |      :|   0x000008f6      4883c408       add rsp, 8
        /      :|   0x000008fa      c3             ret
