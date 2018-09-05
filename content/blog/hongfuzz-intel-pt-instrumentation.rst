:date: 2018-09-05
:slug: hongfuzz-intel-pt-instrumentation
:title: Internals of Hongfuzz - Intel PT
:category: Tools
:tags: fuzzing, reversing
:image: https://raw.githubusercontent.com/google/honggfuzz/master/screenshot-honggfuzz-1.png

TLDR
====

Intel Processor Trace is a hardware level execution tracing utility provided by Intel. The information provided is highly compressed allowing
passing of granular information. So, instead of using QEMU for coverage guided blackbox fuzzing, Intel-PT should provide a rather performant
way.

Recap
=====

Before proceeding further, it is recommended to read through `afl compile time instrumentation <{filename}afl-internals-compile-time-instrumentation.rst>`_
to understand coverage guided fuzzing and then `afl qemu instrumentation <{filename}afl-internals-qemu-instrumentation.rst>`_ to get hold of how QEMU
can be used to trace basic block execution.

1. Intel PT
===========

`Intel Processor Trace <https://software.intel.com/en-us/blogs/2013/09/18/processor-tracing>`_ was introduced starting with 5th gen Intel core processors.
Linux included this in `perf tool kit <https://raw.githubusercontent.com/torvalds/linux/master/tools/perf/Documentation/intel-pt.txt>`_ as a *Performance Monitor Unit*.
The beauty of this is that we can use perf toolkit to trace execution flow of applications.

2. Fuzzing Use Case
===================

Coverage based fuzzing depends on what basic blocks of a program are reached in a fuzzing run. This allows fuzzer to pick subsequent inputs to force
more exploration of previously unseen code paths. First, we will look at how to record an execution trace in userland and then have a look at hongfuzz's
implementation.


Let us take the following simple c code and compile without `PIE <https://en.wikipedia.org/wiki/Position-independent_code#Position-independent_executables>`_
using gcc's **-no-pie** flag.

.. code-block:: c

      int main(int argc, char *argv[])
      {
              if (argc > 1)
                      return -1;
              else
                      return 0;
      }


Above code will produce the following basic blocks in main function.

.. code-block:: terminal

                                                .--------------------------------------.
                                                | (fcn) main 31                        |
                                                |   main (signed int arg1, int arg2);  |
                                                | ; var int local_10h @ rbp-0x10       |
                                                | ; var signed int local_4h @ rbp-0x4  |
                                                | ; DATA XREF from entry0 (+0x21)      |
                                                | push rbp                             |
                                                | mov rbp, rsp                         |
                                                | ; arg1                               |
                                                | mov dword [local_4h], edi            |
                                                | ; arg2                               |
                                                | mov qword [local_10h], rsi           |
                                                | ; [0x1:4]=-1                         |
                                                | ; 1                                  |
                                                | cmp dword [local_4h], 1              |
                                                | jle 0x40111e;[ga]                    |
                                                `--------------------------------------'
                                                        f t
                                                        | |
                                                        | '-------------.
                                          .-------------'               |
                                          |                             |
                                      .-------------------------.   .----------------------------------.
                                      |  0x401117 [gd]          |   |  0x40111e [ga]                   |
                                      | ; -1                    |   | ; CODE XREF from main (0x401115) |
                                      | mov eax, 0xffffffff     |   | mov eax, 0                       |
                                      | jmp 0x401123;[gc]       |   `----------------------------------'
                                      `-------------------------'       v
                                          v                             |
                                          |                             |
                                          '-------------.               |
                                                        | .-------------'
                                                        | |
                                                  .----------------------------------.
                                                  |  0x401123 [gc]                   |
                                                  | ; CODE XREF from main (0x40111c) |
                                                  | pop rbp                          |
                                                  | ret                              |
                                                  `----------------------------------`


Basic blocks at *0x401117* and *0x40111e* are the variable ones here, i.e depending on input program will choose one of these
at runtime.

2.1 perf record
---------------

Let us trace execution flow of the program once without any parameters and once with parameters and record with `perf record <https://linux.die.net/man/1/perf-record>`_.
perf record by default stores the trace data in perf.data and all other perf tools by default read from this file in working directory.

.. code-block:: bash

      $ perf record -e intel_pt//u -- ./a.out
      [ perf record: Woken up 1 times to write data ]
      [ perf record: Captured and wrote 0.010 MB perf.data ]

      # Let us see the basic blocks taken during this execution
      $ perf script --itrace=b | awk "/ main.* main/"

                 a.out 24665 [000] 50879.554567:          1  branches:u:            401115 main+0xf (a.out) =>           40111e main+0x18 (a.out)

In the above case you can see that execution went through basic block *0x40111e*. *-e* in perf record is to specify the kind of event, here we specified *intel_pt*
and *u* stands for userspace. Have a look at linux intel-pt docs for more configuration options. Let us rerun with parameters this time.

.. code-block:: bash

      $ perf record -e intel_pt//u -- ./a.out parameter
      [ perf record: Woken up 1 times to write data ]
      [ perf record: Captured and wrote 0.010 MB perf.data ]

      # Let us see the basic blocks taken during this execution
      $ perf script --itrace=b | awk "/ main.* main/"

                 a.out 26225 [001] 51458.418505:          1  branches:u:            40111c main+0x16 (a.out) =>           401123 main+0x1d (a.out)

Here since the first jump didn't happen, we only see the second jump i.e from basic block starting at *0x40111c* to *0x401123*. This is more passive way of analyzing
already stored trace of an execution.

2.2 perf_event_open
-------------------

`perf_event_open <http://man7.org/linux/man-pages/man2/perf_event_open.2.html>`_ is the programmatic way of doing the same. That man page does better
job of explaining than I ever can.

2.3 Hongfuzz
------------

* Hongfuzz `uses <https://github.com/google/honggfuzz/blob/cc6b929d45b8bbfb3e28617ab511a2b23b5aa962/linux/perf.c#L116>`_ this api to leverage basic block tracing.
* Then it mmaps this filedescriptor to enable reading sampled events from the ring buffer in userspace.
* Subsequently it leverages Intel's `libipt <https://github.com/01org/processor-trace/blob/master/doc/howto_libipt.md>`_ to decode these event packets.
* `Updates <https://github.com/google/honggfuzz/blob/cc6b929d45b8bbfb3e28617ab511a2b23b5aa962/linux/pt.c#L47>`_ it's feedback map based on the events.

.. code-block:: c

      __attribute__((hot)) inline static void perf_ptAnalyzePkt(run_t* run, struct pt_packet* packet) {
          if (packet->type != ppt_tip) {
              return;
          }

          uint64_t ip;
          switch (packet->payload.ip.ipc) {
              case pt_ipc_update_16:
                  ip = packet->payload.ip.ip & 0xFFFF;
                  break;
              case pt_ipc_update_32:
                  ip = packet->payload.ip.ip & 0xFFFFFFFF;
                  break;
              case pt_ipc_update_48:
                  ip = packet->payload.ip.ip & 0xFFFFFFFFFFFF;
                  break;
              case pt_ipc_sext_48:
                  ip = sext(packet->payload.ip.ip, 48);
                  break;
              case pt_ipc_full:
                  ip = packet->payload.ip.ip;
                  break;
              default:
                  return;
          }

          ip &= _HF_PERF_BITMAP_BITSZ_MASK;
          register uint8_t prev = ATOMIC_BTS(run->global->feedback.feedbackMap->bbMapPc, ip);
          if (!prev) {
              run->linux.hwCnts.newBBCnt++;
          }
          return;
      }

Leveraging hardware tracing features like these will enable blackbox coverage guided fuzzing to be a lot faster than usermode translation hooks
like that were done in AFL QEMU's case. There also exists a `AFL fork <https://github.com/hunter-ht-2018/ptfuzzer>`_ leveraing Intel PT .
