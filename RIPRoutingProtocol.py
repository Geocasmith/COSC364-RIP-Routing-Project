

"""
TODO: OUTPUT field is in 5000-1-1, error checker would not accept "1" value. Need a function to split it up into the output field and store the 1's in object. Make class for output
Go through all of the routers outputports,add up all of the values to get the distances
"""

import json, socket, sys, select, time, random, unicodedata

inputSockets = []
def main():
    filename = sys.argv[1]  
    
    #Runs parser, creates sockets for neighbours
    outputClass = parser(filename)
    outputClass.createSockets()
    outputClass.printAll()
    
    #Loops infinitely to simulate sending of rip routing packets to neighbors and recieve packets
    while (1):
        outputClass.sendToNeighbors()
        outputClass.recievePacket(outputClass.recievingPort())
        time.sleep(random.uniform(0.8,1.2)) #each router will send out an update packet at a random interval between 0.8 and 1.2s
        outputClass.checkNeighbors()
        

"""
Router Class which holds all the information on routers and methods related to the routers
"""
class Router:
    def __init__(self,routerID, inputPorts, outputPorts):
        self.routerID = routerID
        self.IP = "127.0.0.1"
        self.inputPorts = inputPorts #input ports specificed in specification sheet
        self.outputPorts = outputPorts #output ports specificed in specification sheet
        self.routingTable = {self.routerID: [0, self.routerID, self.routerID]} #routing table which holds the routers current routing table
        self.inputSockets = [] #holds the socket objects
        self.neighbors = {} #holds neighbors in a dictionary to query the time since the router has recieved info
        
    
    "Finds the port currently recieving packets"
    def recievingPort(self):
        inputs = self.inputSockets
        outputs = []
        readable, writable, exceptional = select.select(inputs, outputs, inputs, 1)
        return readable
    
    "Uses the recievingPort to recieve the packet in the port. The data variable is the recieved JSON packet, this is passed into the function to query if the routers are in the routing table"
    def recievePacket(self, readable):
        for socketObject in readable:
            data, addr = socketObject.recvfrom(4096)
            self.checkIfInRoutingTable(data)
            self.checkForUpdates(data)
            self.setNeighborsTime(data)
            

    "Sets all the neihbours in dictionary to the current time from the packet recieved"
    def setNeighborsTime(self, packet):
        JSONPacket = json.loads(packet)
        routerID = int(JSONPacket["headerInfo"][3]) # Router ID of current Packet sending info
        lastPacketRecieved = time.time()
        self.neighbors[routerID] = lastPacketRecieved
        
    "Goes through list of neighbours and prints off their time, this will show all of their times and when they were last updated"        
    def checkNeighbors(self):
        
        #sets the current time for reference
        currentTime=time.time()
        
        #Goes through all the neighbors and sees if they have not responded within a time period
        for neighbor in self.neighbors:
            neighborTime = self.neighbors[neighbor]
            
            #If the neighbor has not responded in 6 seconds calls timeout, if more than 10 then calls garbage collection
            if(currentTime - neighborTime)>6 and (currentTime - neighborTime)<8:
                self.timeout(neighbor)
            elif(currentTime - neighborTime)>10 and (currentTime - neighborTime)<20:
                self.garbageCollection(neighbor)
                
    "By timing out, the router finds the neighbors row in the routing table and sets its metric as 24 which is 'infinite' and unreachable"            
    def timeout(self,neighbor):
         self.routingTable[neighbor][0] = 24
         for ID in self.routingTable:
             if (self.routingTable[ID][2]) == int(neighbor):
                self.routingTable[ID][0] = 24
         self.printRoutingTable()
         self.sendToNeighbors()

    "Garbage collection removes the unresponsive neighbors row from the routing table"
    def garbageCollection(self,neighbor):
        self.routingTable.pop(neighbor, None)
        self.printRoutingTable()

    "The router will drop routing table rows which its neighbors send to it where the neighbors learned the route from the router so implement split horizon"        
    def splitHorizon(self, table):
        
        #Goes through the routing table and sees if the ID in the learned from field is its own, if it is then it will stop the packet from updating its routing table
        for key in table:
           if int(table[key][2]) == int(self.routerID):
               table[(key)][0] = 24
        return table
    
    "Parses the packet recieved, runs a consistency check, runs split horizon and then updates the routers routing table based on the packet info"    
    def checkForUpdates(self, packet):   
        JSONPacket = json.loads(packet)
        
        #Checks for consistency and if failed, will drop the packet by not updating any values.
        consistency = self.consistencyCheck(JSONPacket) # 0 means pass, 1 means fail and it will drop the packet
        if consistency == 1:
            print("Packet {} dropped for inconsistency".format(JSONPacket))
            return
        
        #Gets the values from the packet header and sets them
        routerID = int(JSONPacket["headerInfo"][3]) # Router ID of current Packet sending info
        metric = int(JSONPacket["headerInfo"][4]) # Metric of nrighbour sending packet to this router
        flag = int(JSONPacket["headerInfo"][5]) #CHANGE        
        recievedTable = JSONPacket["packetTables"] # Routing table recived from neighbor
        routerKeys= self.routingTable.keys()
        
        #Runs split horizon on the table recieved
        recievedTable = self.splitHorizon(recievedTable)
       

        #Converts the routing table keys from unicode to python string to allow the code to compare keys without running into errors
        for key in recievedTable:
            newKey = (unicodedata.normalize('NFKD', key).encode('ascii', 'ignore'))
            recievedTable[newKey] = recievedTable.pop(key)
        
        #Goes through each destination path in routing table
        for key in recievedTable: 
            key = int(key)
            
            #Checks if there is already a metric value for the route
            if key in routerKeys: 
                currentMetric = self.routingTable[int(key)][0] # Current cost to get to that route
                newMetric = metric + recievedTable[str(key)][0] # Cost to go througfh the new path
                
                #If there is a new route recieved from the same router, which occurs when a router is removed, the routing table will be update with the new route and metric
                if (routerID) == (int(self.routingTable[key][2])):
                    self.routingTable[int(key)][0] = newMetric
                    self.printRoutingTable()
                
                #Compares the metric values with the current and recieved table and updates to the shorter path
                if (newMetric < currentMetric): # If the new path is better than the old path 
                    self.routingTable[int(key)] = [newMetric, routerID, routerID] # add the new path cost and new next hop to the routing table
                    self.printRoutingTable()

    "Makes sure all the values in the header of the packet are correct or within a correct range. Returns 0 for correct packets and 1 for inconsistent packets"
    def consistencyCheck(self,packet):
        if len(packet["headerInfo"]) != 6:
            return 1
        elif packet["headerInfo"][0]!=2:
            
            return 1
        elif packet["headerInfo"][1]!=2:
            return 1
        elif packet["headerInfo"][2]!=0:
            return 1
        elif packet["headerInfo"][4]<1:
            return 1
        elif (packet["headerInfo"][5]!=0 and packet["headerInfo"][5]!=1):
            return 1
        else:
            return 0
        
    "Prints the current routing table stored in the router"
    def printRoutingTable(self):
        routingTable = self.routingTable
        print("")
        print("Routing Table update for Router: {}".format(self.routerID))
        print("")
        for key in routingTable:
            reachability = routingTable[key][0]
            if routingTable[key][0] >= 24:
                reachability = "Unreachable"
            print("Destination: {}   Metric: {}    Next Hop: {}  Route From: {}".format(key, reachability, routingTable[key][1], routingTable[key][2]))
        print("")
        print("--------------------------------------------------------------")
        
        
        
        
    def checkIfInRoutingTable(self, packet):
        JSONPacket = json.loads(packet)
        routerID = int(JSONPacket["headerInfo"][3]) # Router ID of current Packet sending info
        metric = int(JSONPacket["headerInfo"][4]) # Metric of nrighbour sending packet to this router
        routerKeys = self.routingTable.keys()
        
        #Adds the neighbor it recieved the packet from to its routing table if it is not currently there
        if not routerID in routerKeys:
            self.addToRoutingTable(routerID, metric, routerID)            
            self.printRoutingTable()
        
        RIPTable = JSONPacket["packetTables"] #Sets recieved packet RIP table to RIPTable
        
        #Converts the routing table keys from unicode to python string to allow the code to compare keys without running into errors
        for key in RIPTable:
            newKey = (unicodedata.normalize('NFKD', key).encode('ascii', 'ignore'))
            RIPTable[newKey] = RIPTable.pop(key)

        #Goes through the recieved RIP Table and compares the values to the routers own RIP table. 
        for TableID in RIPTable:
            TableID = int(TableID)
            if not TableID in routerKeys:
                if TableID != int(self.routerID):
                    
                    #Adds missing table values to the routers RIP Table
                    nextHop = routerID 
                    vectorCost = metric + RIPTable[str(TableID)][0]
                    self.addToRoutingTable(TableID, vectorCost, nextHop)
                    self.printRoutingTable()
            
     
    "Helper function to add new values to the routers routing table"   
    def addToRoutingTable(self, routerID, metric, nextHop):
        self.routingTable[routerID] = ([metric, nextHop, nextHop])
        
    "Creates the message for the package that will be sent, creates the header and adds the whole routing table into JSON"
    "Packet headerInfo= [command,version,0,routerID,metric]"
    def createPacket(self, port):
        headerInfo=[2,2,0,self.routerID, port[1],0] #command is 2, version is 2, last bit must be 0, flag=0 (not flagged)
        ["Came from router {}".format(self.routerID)]
        packetTables=self.routingTable
        packet = {}
        packet['headerInfo'] = headerInfo
        packet['packetTables']=packetTables
        return json.dumps(packet)
        
    "Sends packets to all neighbours specified in the outputports"
    def sendToNeighbors(self):
        for port in self.outputPorts:            
            self.sendPacket(port[0], self.createPacket(port).encode('ascii'))

    "Helper function to send a packet to a port"
    def sendPacket(self,Port, Message):
        IP = "127.0.0.1"
        PORT = int(Port)
        MESSAGE = Message.encode('ascii')
        
        #Creates socket object and sends the message
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.sendto(MESSAGE, (IP, PORT))

    "Function Creates Sockets for all input ports"
    def createSockets(self):
        for port in self.inputPorts:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            UDP_IP = "127.0.0.1"
            UDP_PORT = int(port)
            sock.bind((UDP_IP, UDP_PORT))
            self.inputSockets.append(sock)

    "Prints all the fields in the router"
    def printAll(self):
        print("Router ID: "+self.routerID)
        print("Input Ports: ")
        print(self.inputPorts)
        print("\n")
        print("Output Ports: ")
        print(self.outputPorts)
        print("\n")
        print("Input Sockets: ")
        print(self.inputSockets)
        print("\n")
        
     

"Parser function which gets the config file and extracts the values from it to create a router object"
def parser(filename):
    #Opens file
    file = open(filename,mode='r')
    JSONString = file.read()

    #Gets JSON from file and print it, can query. Sets JSON parts to variables
    RouterInfo = json.loads(JSONString)
    routerID = RouterInfo["router-id"]
    ports = RouterInfo["ports"]
    outputs = RouterInfo["outputs"]
    
    file.close()
    splitOutputs = splitOutput(outputs)    
    
    #checks for missing parameter field
    if not RouterInfo["router-id"] or not RouterInfo["ports"] or not RouterInfo["ports"] :
        error("Missing config parameter")
    
    valid_ID(routerID)
    valid_ports(ports)
    valid_outputs(splitOutputs)
    common_data(ports, splitOutputs)
    
    outputClass = Router(routerID,ports,splitOutputs)
    addPortsToList(ports)
    
    return outputClass
"""
Helper Functions
"""
"Class that adds input ports to global list so we can make sockets for each port"
def addPortsToList(ports):
    for p in ports:
        inputSockets.append(p)
        
"Helper method to see if ID is valid"
def valid_ID(routerID):
    if not (routerID).isdigit() or not int(routerID) in range(1,64001):
        error("Invalid router ID")    

"Helper method to see if ports are valid"
def valid_ports(ports):
    duplicatePorts = []
    for port in ports:
        if port in duplicatePorts:
            error("Invalid Port/s")
        
        #DuplicatePorts stores ports parsed so ensure the same port is not specified twice
        duplicatePorts.append(port)

"Helper method to see if outputs are valid"
def valid_outputs(outputs):
    duplicateOutputs = []
    for output in outputs:
        if output[0] in duplicateOutputs:
            error("Invalid Output/s")
        
        #DuplicatePorts stores ports parsed so ensure the same port is not specified twice
        duplicateOutputs.append(output[0])        

"Function to check if any of the input ports are not the same as the outputs"
def common_data(ports, outputs): 
    equal = False
   
    #traverses list and checks to see if any are the same or if the port or output are out of bounds
    for port in ports:  
        for output in outputs: 
            if port == int(output[0]) or not port in range(1024,64001) or not int(output[0]) in range(1024,64001): 
                equal = True
                error("Invalid ports/outputs")
    return equal

"Helper method to split up output port string eg [5000-1-1] into 3 values"
def splitOutput(outputs):
    splitOutputs = []
    for output in outputs:  
        output = output.split("-")
        splitOutputs.append(output)
    return splitOutputs

"Helper function to raise an error in the code. Used for exiting script via exception"
def error(errorMessage):
    raise Exception(errorMessage)

"""
END PARSER FUNCTION
"""
    
main()

