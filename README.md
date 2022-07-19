# COSC364RipRouting
In this project, in groups of two, we implemented the RIP routing protocol on python. We created a file parser so parse the configuration files, implemented the core of the RIP Routing protocol and then implemented split horizon with poisoned reverse.
The code can be run in the terminal by downloading and inputting "RIPRoutingProtocol.py routerConfig#" and replacing X with the number of the configuration file you want to use. 
To see a demonstration of the network it is advised that you run 7 instances of the terminal, all using separate routing configuration files.

## Instructions for running the project 
1. Download the project zip file
2. On linux, navigate to the source code folder and run the following commands to start the servers
RIPRoutingProtocol.py routerConfig1
RIPRoutingProtocol.py routerConfig2
RIPRoutingProtocol.py routerConfig3
RIPRoutingProtocol.py routerConfig4
RIPRoutingProtocol.py routerConfig5
RIPRoutingProtocol.py routerConfig6
RIPRoutingProtocol.py routerConfig7
3. The servers will now be started, they will use the protocol to form a network. Each server will display a routing table. Closing any of the running python scripts will simulate a server in the network going down. Routes between the remaining servers will be adjusted to account for the server going down. Rerunning the command to start the server will simulate the server going back up. The routes will then be recalculated.
