Quickstart
==========

Fast path
---------

If you want to get moving immediately, use this minimal setup:

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   make dev
   pycycle-mcp --transport stdio

Then come back to the sections below for validation, examples, and workflow
details.

Setup
-----

Create a local virtual environment and install the development dependencies:

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   make dev

Run the default quality gates:

.. code-block:: bash

   make test
   make ci

Start the server
----------------

Run the CLI over stdio:

.. code-block:: bash

   pycycle-mcp --transport stdio

Inspect a non-blocking HTTP configuration example:

.. code-block:: bash

   PYTHONPATH=src python3 examples/server/http_launch_config.py

Current capability notes
------------------------

- Default tests and examples target deterministic stand-ins and avoid requiring
  real pyCycle/OpenMDAO assets.
- Output schemas and tool names are stable.
- Runtime integration with real OpenMDAO/pyCycle should be validated with
  optional integration workflows.
