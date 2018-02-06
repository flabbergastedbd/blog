:date: 2018-02-06
:slug: afl-internals-qemu-instrumentation
:title: Internals of AFL fuzzer - QEMU Instrumentation
:category: Tools
:tags: fuzzing, reversing, afl
:image: https://image.slidesharecdn.com/qemu-binarytranslation-140930222818-phpapp02/95/qemu-binary-translation-10-638.jpg

Introduction
============

If you need an introduction to `AFL <http://lcamtuf.coredump.cx/afl/>`_, you have probably missed out a lot in the instrumented binary fuzzing saga
for the past couple of years. **afl-fuzz**\ (fuzzer part of this toolset) is extremely fast, easy to use and requires minimal configuration.
Technical details of AFL are available `here <http://lcamtuf.coredump.cx/afl/technical_details.txt>`_. All this awesomeness is written in C, a
language that I almost never used. So I wanted to try and understand the implementation i.e How ideas were translated to code in AFL.

Before proceeding further, it is recommended to read through `afl compile time instrumentation <{filename}afl-internals-compile-time-instrumentation.rst>`_.
Now, what about the black box binaries for which source code is unavailable?? Instrumentation is used to

- Trace the execution flow of basic blocks for the specificied fuzzy input.
- Save time by fuzzing in a `forkserver model <https://lcamtuf.blogspot.in/2014/10/fuzzing-binaries-without-execve.html>`_.

One way is to parse the given binary and rewrite it along with the instrumentation (afl-dyninst).

1. QEMU
=======

`QEMU <https://www.qemu.org/>`_ is also a process emulator that lets you run different architectures on a single machine by doing dynamic translation.

1.1 Binary Translation
----------------------

Read `qemu binary translation <https://www.slideshare.net/RampantJeff/qemu-binary-translation>`_. QEMU can

- Translate basic blocks of one architecture (target i.e arch being emulated) to another (host i.e arch on which qemu is being run).
- Store the translated blocks (**TB**) in translated block cache (**TBC**) enabling translate once and use multiple times.
- Add prologue and epilogue to basic blocks to handle operations like jumps between basic blocks, restoring control etc..

.. image:: https://wiki.xen.org/images/thumb/d/d0/F-t-2.jpg/600px-F-t-2.jpg
        :align: center

1.2 Execution flow
------------------

Let us walk through an abstracted qemu execution run

.. image:: https://image.slidesharecdn.com/qemu-binarytranslation-140930222818-phpapp02/95/qemu-binary-translation-10-638.jpg
        :align: center

- Start the pre-generated code prologue, i.e initialize the process and jmp to **_start** of the binary.
- Look for the translated block containing the **_start** program counter (PC) in the cache. If no, generate translation and cache it.
- Jump to the translated block and execute it.
- On next jump, repeat from the cache search.

.. image:: https://image.slidesharecdn.com/qemu-binarytranslation-140930222818-phpapp02/95/qemu-binary-translation-15-638.jpg
        :align: center

2. Idea
=======

We need to find the function in qemu that gets called for executing a translated block. Keep in mind that
qemu and the binary run in the same process, so this allows us to write instrumentation in C and `patch
<https://github.com/mcarpenter/afl/tree/master/qemu_mode/patches>`_ qemu source.

2.1 Coverage Instrumentation
----------------------------

.. code-block:: c

	cur_loc  = (cur_loc >> 4) ^ (cur_loc << 8);
	cur_loc &= MAP_SIZE - 1;

	/* Implement probabilistic instrumentation by looking at scrambled block
	address. This keeps the instrumented locations stable across runs. */

	if (cur_loc >= afl_inst_rms) return;

	afl_area_ptr[cur_loc ^ prev_loc]++;
	prev_loc = cur_loc >> 1;

2.2. Communication
------------------

**Same as compile time instrumentation**

- AFL uses forkserver model to fuzz a program. For more info on the forkserver model of fuzzing, check `this <https://lcamtuf.blogspot.in/2014/10/fuzzing-binaries-without-execve.html>`_.
- Instance of the qemu running the target will be used as a forkserver which will communicate with the fuzzer process via fds 198 (control queue) & 199 (status queue).
- Clones of this forkserver instance are used to run the testcases. So, techically the actual fuzzy input execution happens in grandchildren process of the fuzzer.
- The execution trace from the target is available via shared memory (shm) to the fuzzer process.

**QEMU specific tweaks**

- An additional fd is used to relay *needs translation* messages between child and forkserver. If you recall qemu translation of basic blocks are done on a need basis. When
  a new basic block is encoutered in child, the forksever is made aware of the arguments (like pc, code segment base, flags) required for translation of that block. This allows
  the forkserver to cache the translation block by performing the translation in it's process. All the subsequent children cloned from the forkserver, will have the new TB in
  the cache.

3. Implementation
=================

3.1 QEMU Patches
----------------

- `cpu_tb_exec() <https://github.com/qemu/qemu/blob/4124ea4f5bd367ca6412fb2dfe7ac4d80e1504d9/accel/tcg/cpu-exec.c#L140>`_ is responsible for executing a TB and
  information such as *pc* address is available there. If you recall the compile time instrumentation where we used random constants for tracing, here we can use
  *pc* address of basic block as the constant.

	.. code-block:: c

		/* Execute a TB, and fix up the CPU state afterwards if necessary */
		static inline tcg_target_ulong cpu_tb_exec(CPUState *cpu, TranslationBlock *itb)
		{
		    CPUArchState *env = cpu->env_ptr;
		    uintptr_t ret;
		    TranslationBlock *last_tb;
		    int tb_exit;
		    uint8_t *tb_ptr = itb->tc.ptr;

		    /* AFL Instrumentation here */

		    if(itb->pc == afl_entry_point) {
			    afl_setup();
			    afl_forkserver(cpu);
		    }
		    afl_maybe_log(itb->pc);

		    /* End AFL Instrumentation here */

		    qemu_log_mask_and_addr(CPU_LOG_EXEC, itb->pc,
					   "Trace %d: %p ["
					   TARGET_FMT_lx "/" TARGET_FMT_lx "/%#x] %s\n",
					   cpu->cpu_index, itb->tc.ptr,
					   itb->cs_base, itb->pc, itb->flags,
					   lookup_symbol(itb->pc));
		 ....


- `tb_find() <https://github.com/qemu/qemu/blob/4124ea4f5bd367ca6412fb2dfe7ac4d80e1504d9/accel/tcg/cpu-exec.c#L379>`_ is responsible for finding a TB based on
  current state. This function takes care of cache lookup and calls `tb_gen_code() <https://github.com/qemu/qemu/blob/4124ea4f5bd367ca6412fb2dfe7ac4d80e1504d9/accel/tcg/cpu-exec.c#L404>`_
  incase of translation required. We can add `afl_request_tsl() <https://github.com/mcarpenter/afl/blob/master/qemu_mode/patches/afl-qemu-cpu-inl.h#L257>`_ here to signal
  `forkserver to translate <https://github.com/mcarpenter/afl/blob/master/qemu_mode/patches/afl-qemu-cpu-inl.h#L277>`_ and keep this block in its memory for future clones. The
  parameters required for translation are constructed into a struct and passed.

	.. code-block:: c

		struct afl_tsl t;

		if (!afl_fork_child) return;

		t.pc      = pc;
		t.cs_base = cb;
		t.flags   = flags;

		if (write(TSL_FD, &t, sizeof(struct afl_tsl)) != sizeof(struct afl_tsl))
			return;

- `elfload.patch <https://github.com/mcarpenter/afl/blob/master/qemu_mode/patches/elfload.diff>`_ to record the *afl_entry_poiunt*, *afl_start_code* & *afl_end_code*. These attributes
  are used in `afl_maybe_log()`_ for some bounds check.
- `syscall.patch <https://github.com/mcarpenter/afl/blob/master/qemu_mode/patches/syscall.diff>`_ to pass the right *pid* and *tgid* incase of *SIGABRT* on forkserver.

3.2 AFL Patches
---------------

These are just plain C ports of the existing assembly.

- `afl_maybe_log() <https://github.com/mcarpenter/afl/blob/master/qemu_mode/patches/afl-qemu-cpu-inl.h#L227>`_ is the function that is calls setup for the first time and
  updates shared tracing memory for every execution of a TB.
- `afl_setup() <https://github.com/mcarpenter/afl/blob/master/qemu_mode/patches/afl-qemu-cpu-inl.h#L107>`_ setups the shared memory in the child process. This SHM is where
  the 64kB trace data array is stored.
- `afl_forkserver() <https://github.com/mcarpenter/afl/blob/master/qemu_mode/patches/afl-qemu-cpu-inl.h#L160>`_ is responsible for creation of forkserver and listen
  on fd for launching clones.

**PS**: Considering what QEMU is capable of, I was amazed by the simplicity of this `patch`_ which required no major modifications to **afl-fuzz**.
