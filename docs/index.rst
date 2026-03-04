pycycle-mcp
===========

`pycycle-mcp` exposes deterministic, JSON-friendly pyCycle/OpenMDAO tools
through an MCP server surface. The implementation keeps local docs/tests stable
without requiring live pyCycle/OpenMDAO runtime assets for every workflow.

Get Started Fast
----------------

If you are new to the project, this is the fastest path:

1. Create a virtual environment and install the local toolchain.
2. Run the test suite once.
3. Start the MCP server over stdio.

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   make dev
   make test
   pycycle-mcp --transport stdio

For the fuller setup flow, go straight to :doc:`quickstart`.

.. toctree::
   :maxdepth: 1

   Quickstart <quickstart>
   Python API <api>
   Runtime Guides <reference/index>
   Examples <examples/index>
