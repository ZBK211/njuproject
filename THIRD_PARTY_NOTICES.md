# Third-Party Notices

ForgeAgent was developed as an independent coding agent. Its project-memory design was informed by the Apache-2.0 project `dsh-memoir`:

https://github.com/Qinling-Melon-Farmers/dsh-memoir

No vendored `dsh-memoir` source tree is required at runtime. The local `tmp/dsh-memoir` clone is used only for comparison and should not be included in the final public repository.

The visual demo flow was also informed by the MIT-licensed `GenericAgent` project and the user's local previous reproduction:

https://github.com/Isdefine/GenericAgent

ForgeAgent does not vendor GenericAgent as a runtime dependency. Its independent core loop, tools, parser, memory layer, and demo backend live in this repository.
