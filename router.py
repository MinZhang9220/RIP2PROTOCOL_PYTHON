"""
This module describe one router,it contains router basic fields and functions.
- Basic fields
1: router_id,int, unique id of one router
2: input_ports,list, this is the set of port numbers (and underlying sockets)
on which the instance of the routing demon will listen for incoming routing
packets from peer routing demons. There needs to be a separate input port for
each neighbor the router has
3: output_ports,dict: {dst,(cst, port)}, specify the ¡°contact information¡± for
neighboured routers about cost and port.
4: address, 127.0.0.1
5: routing_table,dict: {dst: (cst, nexthop, g_timeout,d_timeout)}, specify the
routing table,g_timeout for timeout,
and d_timeout for garbage collection.
6: sockets, dict: {port: socket}, specify the socket and the binded port.
7: sender,socket, do the sending work
"""
import socket
from threading import Timer
import select
import ast
import random
import datetime
RIP_VERSION = 2
LENGTH_VERSION_NUM = 4
LENGTH_SOURCE_ROUTER_ID = 16
LENGTH_DESTINATION_ROUTER_ID = 16
LENGTH_COMMAND = 4
INDEX_OF_LINK_COST = 0
INDEX_OF_NEXT_HOP = 1
INDEX_OF_G_TIMEOUT = 2
INDEX_OF_D_TIMEOUT = 3
GARBAGE_TIMEOUT = 60
DELETE_TIMEOUT = 40
TIMER_VALUE_FOR_PERIOD_UPDATE = 10
MAX_LINK_COST = 16
TIMER_VALUE_FOR_TIME_OUT = 1
COMMAND_VALUE_FOR_UPDATE_ROUTING_TABLE = 1
class Router:
    def __init__(self, router_id, input_ports, output_ports):
        """
        :param router_id:
        :param input_ports:
        :param output_ports:
        """
        self.router_id = router_id
        self.input_ports = input_ports
        self.output_ports = output_ports
        self.address = "127.0.0.1"
        self.routing_table = {}
        self.sockets = {}
        self.sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for port in self.input_ports:
            # Creates as many UDP sockets as it has input ports and binds one socket
            # to each port.
            self.sockets[port] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sockets[port].bind((self.address, port))
    def initialise_routing_table(self):
        """
        initialise routing table
        """
        self.routing_table[self.router_id] = (0, self.router_id, 0, 0)
    def pack_routing_table(self, sending_routing_table):
        """
        Pack routing table and return a byte
        :param sending_routing_table:
        :return: encoded_routing_table
        """
        encoded_routing_table = str(sending_routing_table).encode()
        return encoded_routing_table
    def unpack_routing_table(self, packet):
        """
        Unpack routing table and return a dictionary routing table
        :param packet:
        :return: decoded_routing_table
        """
        temp = packet[40:].decode()
        decoded_routing_table = ast.literal_eval(temp)
        return decoded_routing_table
    def pack_common_RIP_packet(self, dst_router, command):
        """
        Pack common information of a rip packet and return a byte
        :param dst_router:
        :param command:
        :return: common_RIP_packet
        """
        encoded_version_id = bin(RIP_VERSION).replace('0b',
        '').zfill(LENGTH_VERSION_NUM)
        encoded_source_router_id = bin(self.router_id).replace('0b',
        '').zfill(LENGTH_SOURCE_ROUTER_ID)
        encoded_destination_router_id = bin(dst_router).replace('0b',
        '').zfill(LENGTH_DESTINATION_ROUTER_ID)
        encoded_command = bin(command).replace('0b', '').zfill(LENGTH_COMMAND)
        common_RIP_packet = (encoded_version_id + encoded_source_router_id +
        encoded_destination_router_id + encoded_command).encode()
        return common_RIP_packet
    def unpack_common_RIP_packet(self, packet):
        """
        Unack common rip packet and return a tuble
        :param packet:
        :return: decoded_common_RIP_packet
        """
        decoded_pack = packet.decode()
        version = int(decoded_pack[ : 4], 2)
        source_router_id = int(decoded_pack[4 : 20], 2)
        destination_router_id = int(decoded_pack[20 : 36], 2)
        command = int(decoded_pack[36 : 40], 2)
        decoded_common_rip_packet = (source_router_id, destination_router_id, command)
        return decoded_common_rip_packet
    def timer_for_router(self):
        """
        1.Timer for this router to timeout one route and delete this route.
        2.The garbage collection time is 180s and the delete time is 120s.
        3.Change route cost from this router to garbage router to 16 and advertise
        this router's routing table to neighbours when garbage collection time is
        180s
        4.Delete route from this router to garbage router when the delete time is 120
        and then advertise this router's routing table to neighbours.
        :return:
        """
        invalid_des = []
        for des, routeinfo in self.routing_table.items():
            if self.routing_table[des][INDEX_OF_D_TIMEOUT] == DELETE_TIMEOUT:
                invalid_des.append(des)
                continue
            if des != self.router_id:
                if self.routing_table[des][INDEX_OF_G_TIMEOUT] < GARBAGE_TIMEOUT and \
                self.routing_table[des][INDEX_OF_LINK_COST] != MAX_LINK_COST:
                    self.routing_table[des] = (self.routing_table[des][INDEX_OF_LINK_COST],
                    self.routing_table[des][INDEX_OF_NEXT_HOP],
                    self.routing_table[des][INDEX_OF_G_TIMEOUT] + 1,
                    self.routing_table[des][INDEX_OF_D_TIMEOUT])
                elif self.routing_table[des][INDEX_OF_G_TIMEOUT] == GARBAGE_TIMEOUT:
                    self.routing_table[des] = (MAX_LINK_COST,self.routing_table[des][INDEX_OF_NEXT_HOP],
                    GARBAGE_TIMEOUT,self.routing_table[des][INDEX_OF_D_TIMEOUT] + 1)
                    if self.routing_table[des][INDEX_OF_D_TIMEOUT] == 1:
                        print("At time: " + str(datetime.datetime.now()) + " "
                        "Advertise routing table: Can not connect to {0:1d} after ".format(des) + str(GARBAGE_TIMEOUT) + "s.")
                    self.advertise_routing_table()
                elif self.routing_table[des][INDEX_OF_LINK_COST] == MAX_LINK_COST and self.routing_table[des][INDEX_OF_G_TIMEOUT] != GARBAGE_TIMEOUT:
                    self.routing_table[des] = (MAX_LINK_COST,
                    self.routing_table[des][INDEX_OF_NEXT_HOP],
                    self.routing_table[des][INDEX_OF_G_TIMEOUT],
                    self.routing_table[des][INDEX_OF_D_TIMEOUT] + 1)
                if len(invalid_des) > 0:
                    for des in invalid_des:
                        self.routing_table.pop(des)
                        print("At time: " + str(datetime.datetime.now()) + " " +
                        "Delete route from {0:1d} to {1:1d}".format(self.router_id,
                        des))
                        print("At time: " + str(datetime.datetime.now()) + " " + "Advertise routing table: Delete route")
                    self.advertise_routing_table()
                Timer(TIMER_VALUE_FOR_TIME_OUT, self.timer_for_router, args='').start()
    def advertise_routing_table(self):
        """
        Advertise routing table
        """
        try:
            print("\n")
            print("----->Routing table for router " + str(self.router_id))
            print("Print routing table at time: " + str(datetime.datetime.now()))
            self.print_routing_table(self.routing_table)
            print("\n")
            for router, route in self.output_ports.items(): # router to be advertised
                advertised_routing_table = {}
                """
                Implement split-horizon with poisoned reverse.
                For any update message or unsolicited response a separate routing
                table needs to be created for each neighbor.
                """
                for dst, route_info in self.routing_table.items():
                    """
                    'route_info[1] == router and dst != router' means that The router
                    learned this route from this neighbours, the router will not
                    advertise this route to neighbours router.
                    'dst == self.router_id' this means that this route is myself,the
                    router will not advertise this route to neighbours router.
                    """
                    if (route_info[INDEX_OF_NEXT_HOP] == router and dst != router):
                        """ split horizon:"""
                        advertised_routing_table[dst] = (MAX_LINK_COST,
                        route_info[INDEX_OF_NEXT_HOP],
                        route_info[INDEX_OF_G_TIMEOUT], route_info[INDEX_OF_D_TIMEOUT])
                    elif dst == self.router_id:
                        continue
                    else:
                        """
                        Prepare routing table which can be advertised to destination
                        neighbours.
                        """
                        advertised_routing_table[dst] = route_info
                        """
                        If neighbour router are now in the router's routing
                        table,check its cost to the router.
                        If cost is 16, it means that this route is invalid now,the
                        router will not advertise routing table to the neighbour.
                        """
                    if router in self.routing_table.keys():
                        if self.routing_table[router][INDEX_OF_LINK_COST] < MAX_LINK_COST:
                            message = self.pack_common_RIP_packet(router,
                            COMMAND_VALUE_FOR_UPDATE_ROUTING_TABLE) + \
                            self.pack_routing_table(advertised_routing_table)
                            self.sender.sendto(message, (self.address,
                            self.output_ports[router][INDEX_OF_NEXT_HOP]))
                        else:
                            message = self.pack_common_RIP_packet(router,
                            COMMAND_VALUE_FOR_UPDATE_ROUTING_TABLE) + \
                            self.pack_routing_table(advertised_routing_table)
                            self.sender.sendto(message, (self.address,
                            self.output_ports[router][INDEX_OF_NEXT_HOP]))
            # The time for period is uniform distribution
            period = random.uniform(0.8 * TIMER_VALUE_FOR_PERIOD_UPDATE, 1.2 *
            TIMER_VALUE_FOR_PERIOD_UPDATE)
            Timer(period, self.advertise_routing_table, args='').start()
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
    def send_message_to_destination(self, dst, packet):
        """
        Ask neighbours router to print routing table
        :param dst:
        :param packet:
        """
        if dst in self.routing_table.keys():
            if self.routing_table[dst][INDEX_OF_LINK_COST] < MAX_LINK_COST:
                hop = self.routing_table[dst][INDEX_OF_NEXT_HOP]
                port = self.output_ports[hop][INDEX_OF_NEXT_HOP]
                self.sender.sendto(packet, (self.address, port))
            else:
                print("The connect to destination is fail.")
        else:
            print("Destination {0:1d} is not turn on now!".format(dst))
    def calculate_routing_table(self, sender_router, advertised_routing_table):
        """
        Calculate routing table and advertise new routing table if it has been update.
        :param sender_router:
        :param advertised_routing_table:
        """
        print("Unsolicited Routing table from {0:1d}".format(sender_router))
        print("Get Unsolicited routing table at time: " + str(datetime.datetime.now()))
        self.print_routing_table(advertised_routing_table)
        # Old routing table, this routing table is used to compare to new this
        #router's new routing table
        old_routing_table = self.routing_table
        # If advertised routing table is empty, advertise to neighbours.
        if not bool(advertised_routing_table):
            for router, route in self.output_ports.items():
                if sender_router == router:
                    self.routing_table[sender_router] = (route[INDEX_OF_LINK_COST],sender_router, 0, 0)
                    break
        else:
            """
            If advertised routing table is not empty but the destination is not in
            the router's routing table advertise to neighbours
            """
            if not (sender_router in self.routing_table.keys()):
                for router, route in self.output_ports.items():
                    if sender_router == router:
                        self.routing_table[sender_router] = (route[INDEX_OF_LINK_COST], sender_router, 0, 0)
                        break
            for router, route_info in advertised_routing_table.items():
                # update the route cost from sender router to this router
                if router == self.router_id:
                    new_cost = advertised_routing_table[router][INDEX_OF_LINK_COST]
                    self.routing_table[sender_router] = (new_cost, sender_router, 0,
                    0)
                else:
                    # This router already have this route
                    if router in self.routing_table.keys():
                        # This route learned from the sender router, must update
                        if self.routing_table[router][INDEX_OF_NEXT_HOP] == sender_router:
                            new_cost = advertised_routing_table[router][INDEX_OF_LINK_COST] + self.routing_table[sender_router][INDEX_OF_LINK_COST]
                            # If the new cost is greater than 16, change the new cost
                            #equal to 16
                            if new_cost > MAX_LINK_COST:
                                new_cost = MAX_LINK_COST
                            if new_cost == MAX_LINK_COST:
                                self.routing_table[router] = (new_cost, sender_router,
                                0, self.routing_table[router][INDEX_OF_D_TIMEOUT])
                            else:
                                self.routing_table[router] = (new_cost, sender_router,
                                0, 0)
                        else:
                            # Check if has a new route to destination router
                            old_cost = self.routing_table[router][INDEX_OF_LINK_COST]
                            new_cost = advertised_routing_table[router][INDEX_OF_LINK_COST] + self.routing_table[sender_router][INDEX_OF_LINK_COST]
                            if old_cost > new_cost:
                                self.routing_table[router] = (new_cost, sender_router,
                                0, 0)
                    else:
                        # This route is not in the router's routing table,add this
                        # route to routing table
                        new_cost = advertised_routing_table[router][INDEX_OF_LINK_COST] + self.routing_table[sender_router][INDEX_OF_LINK_COST]
                        if new_cost < MAX_LINK_COST:
                            self.routing_table[router] = (new_cost, sender_router, 0,
                            0)
        # Check if the old routing table is same or not as the new routing table.
        if old_routing_table != self.routing_table:
            print("Advertise routing table: There are Changes in routing table")
            self.advertise_routing_table()
    def print_routing_table(self, routing_table):
        """
        :param routing_table:
        :return:
        """
        print("-"*55)
        print("{0:1s}{1:9s}{2:1s}{3:9s}{4:1s}{5:9s}{6:1s}{7:10s}{8:1s}{9:10s}{10:1s}".format("|", "Dst", "|", "Cst", "|","Hop", "|", "Timeout", "|", "Garbage Collection", "|"))
        print("-"*55)
        for key, value in routing_table.items():
            cost = value[INDEX_OF_LINK_COST]
            hop = value[INDEX_OF_NEXT_HOP]
            g_timeout = value[INDEX_OF_G_TIMEOUT]
            d_timeout = value[INDEX_OF_D_TIMEOUT]
            print("{0:1s}{1:9d}{2:1s}{3:9d}{4:1s}{5:9d}{6:1s}{7:10d}{8:1s}{9:10d}{10:1s}".format("|", key, "|", cost, "|", hop, "|", g_timeout, "|", d_timeout , "|"))
            print("-"*55)
    def handle_RIP_packet(self, packet):
        """
        Handle rip packet
        :param packet:
        """
        source_router_id, destination_router_id, command = self.unpack_common_RIP_packet(packet)
        # This packet belong to this router to handle
        if destination_router_id == self.router_id:
            # Calculate routing table
            if command == COMMAND_VALUE_FOR_UPDATE_ROUTING_TABLE:
                self.calculate_routing_table(source_router_id,
                self.unpack_routing_table(packet))
        # Forward this packet to destination router
        else:
            self.send_message_to_destination(destination_router_id, packet)
    def incoming_packet_check(self, pkt):
        version_id = int(pkt.decode("utf-8")[0:4], 2)
        if(version_id != 2):
            return False
        source_router_id = int(pkt.decode("utf-8")[4:20], 2)
        if(source_router_id < 1 or source_router_id > 64000):
            return False
        destination_router_id = int(pkt.decode("utf-8")[20:36], 2)
        if(destination_router_id < 1 or destination_router_id > 64000):
            return False
        command = int(pkt.decode("utf-8")[36:40], 2)
        if(command != 1):
            return False
        routing_table_string = pkt.decode("utf-8")[40:]
        routing_table = ast.literal_eval(routing_table_string)
        for router_id in routing_table.keys():
            matric = routing_table[router_id][0]
            if(matric > 16 or matric < 0):
                return False
        return True
    def switch_on_router(self):
        """
        Switch the router on
        """
        print("\n")
        print("Router Id: {0: 10d}".format(self.router_id))
        print("-"*55)
        print("Common Command:")
        print("2:Print routing table: format(2-dst)\n")
        print("-"*55)
        self.initialise_routing_table()
        self.advertise_routing_table()
        self.timer_for_router()
        rlist = list(self.sockets.values())
        wlist = []
        xlist = []
        while True:
            readable, writable, exceptions = select.select(rlist, wlist, xlist)
            for task in readable:
                # Task is socket
                if task in self.sockets.values():
                    for socket_instance in self.sockets.values():
                        if socket_instance == task:
                            packet, _ = socket_instance.recvfrom(1024)
                            if self.incoming_packet_check(packet) == True:
                                self.handle_RIP_packet(packet)