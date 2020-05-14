#!/usr/bin/env python

import argparse
import codecs
import errno
import glog
import inspect
import ipaddress
import KBHit
import socket
import sys
import time
import threading
from typing import Union

DEBUG_MODE = False

class TcpClient:
    """Simple client for communicating with server via tcp.
    Attributes:
        DEFAULT_BUFFER_SIZE__: Static. A default size of receive buffer. Default: 8192.
        DEFAULT_timeout__: Static. A default receive timeout. Default: 5.
        __socket: A socket that connected to server.
        __server_address: An address indicating connected server address.
        __server_port: An integer indicating connected server port.
        __buffer_size: A size of receive buffer.
        __timeout: A receive timeout.
        __is_connected: A boolean indicating if client is connected.
        __is_receiving: A boolean indicating if receive loop is working.
        __loop: A thread to run receive loop.
        __encoding: A encoding type to decode received message. Default: System default encoding.
    """
    DEFAULT_BUFFER_SIZE__:int = 8192
    DEFAULT_timeout__:int = 5

    def __init__(self):
        self.__socket:socket.socket = None
        self.__server_address:Union[ipaddress.IPv4Address, ipaddress.IPv6Address] = None
        self.__server_port:int = None
        self.__buffer_size:int = self.DEFAULT_BUFFER_SIZE__
        self.__timeout = self.DEFAULT_timeout__
        self.__encoding:str = sys.getdefaultencoding()
        self.__is_connected:bool = False
        self.__is_receiving:bool = False
        self.__loop:threading.Thread = None
        

    # Getter & Setter
    def get_server_address(self):
        """Get connected server ip.
        Returns:
            IPv4Address|ipaddress.IPv6Address. server address if client is conneccted, None otherwise.
        """
        return self.__server_address
    def get_server_port(self):
        """Get connected server port.
        Returns:
            int. Server port if client is connected, None otherwise.
        """
        return self.__server_port
    def get_buffer_size(self):
        """Get buffer size.
        Returns:
            int. Receive buffer size.
        """
        return self.__buffer_size
    def set_buffer_size(self, buffer_size:int):
        """Set receive buffer size.
        Returns:
            bool. True if set was successful, False otherwise.
        """
        if buffer_size < 1:
            return False
        self.__buffer_size = buffer_size
        return True
    def get_timeout(self):
        """Get timeout.
        Returns:
            int. Timeout.
        """
        return self.__timeout
    def set_timeout(self, timeout:int):
        """Set timeout.
        Returns:
            bool. True if set was successful, False otherwise.
        """
        if timeout < 1:
            return False
        self.__socket.settimeout(timeout)
        self.__timeout = timeout
        return True
    def get_encoding(self):
        """Get encoding.
        Returns:
            str. Encoding type.
        """
        return self.__encoding
    def set_encoding(self, encoding:str):
        """Set encoding.
        Returns:
            bool. True if set was successful, False otherwise.
        """
        try:
            codecs.lookup(encoding)
            self.__encoding = encoding
            return True
        except LookupError:
            return False
    def is_connected(self):
        """Get connection state.
        Returns:
            bool. True if client is connected to server, False otherwise.
        """
        return self.__is_connected
    def is_receiving(self):
        """Get receiving state.
        Returns:
            bool. True if client is receiving, False otherwise.
        """
        return self.__is_receiving

    # Control functions
    def connect(self, server_address:Union[ipaddress.IPv4Address, ipaddress.IPv6Address, str], server_port:int, start_receive:bool = False, on_received = None):
        """Connnect to tcp server via ipaddress and port.
        Args:
            server_address: Ip address of valid tcp server.
            server_port: Port of valid tcp server.
            start_receive: True to start receive loop on connection. Default: False.
            on_received: Receive callback for get received data. On None received data will be printed to stdout. Default: None.
        Returns:
            True if connection is successful, False otherwise.
        Raises:
            UserWarning: If client has existing connection this will be raised.
            ConnectionRefusedError: If connection failed this will be raised.
        """
        if self.__is_connected: # Check if client is already connected
            raise UserWarning("The client is already connected to server.\nDisconnect existing connection before making new connection.")
        if type(server_address) is str:
            try: # Check if inputted server address is valid
                self.__server_address = ipaddress.ip_address(server_address)
                glog.debug("Inputted address is valid. Address is " + ("IPv4") if type(server_address) is ipaddress.IPv4Address else ("IPv6"))
            except ValueError:
                try:
                    self.__server_address = ipaddress.ip_address(socket.gethostbyname(server_address))
                    glog.debug("Inputted address is hostname. Address of hostname is " + str(self.__server_address))
                except socket.gaierror:
                    glog.debug("Inputted addres is not valid. Inputted address is " + str(server_address))
                    raise ValueError("Inputted server address is not valid") from None
        else:
            self.__server_address = server_address
            glog.debug("Inputted address is valid. Address is " + ("IPv4") if type(server_address) is ipaddress.IPv4Address else ("IPv6"))

        if not 0 <= server_port < 65535: # Check if inputted server port is valid
            glog.debug("Inputted port is not valid. Port is " + str(server_port))
            raise ValueError("Inputted server port is not valid") from None
        self.__server_port = server_port
        try: # Connect to server
            self.__socket = socket.create_connection((str(self.__server_address), server_port), self.__timeout)
            self.__socket.setblocking(False)
            self.__socket.settimeout(self.__timeout)
            glog.info("Client connected to " + str(self.__server_address) + ":" + str(self.__server_port))
        except (ConnectionRefusedError, socket.timeout):
            raise ConnectionRefusedError("Failed to connect " + str(self.__server_address) + ":" + str(self.__server_port)) from None

        glog.debug("Client encoding is " + str(self.__encoding))
        glog.debug("Client timeout is " + str(self.__timeout))
        self.__is_connected = True
        if start_receive: # Start receive loop
            self.start_receive(on_received)
    def disconnect(self):
        """Disconnect from tcp server.
        Returns:
            True if connection is successful, False otherwise.
        """
        if not self.__is_connected:
            return False
        self.stop_receive()
        self.__socket.close()
        glog.info("Client disconneted from " + str(self.__server_address) + ":" + str(self.__server_port))
        self.__socket = None
        self.__server_address = None
        self.__server_port = None
        self.__is_connected = False
        return True
    def send(self, payload:bytes):
        """Send payload to tcp server.
        Args:
            payload: payload to send.
        Raises:
            UserWarning: If client is not connected to server this will be raised.
            socket.error: If client failed to send payload to server this will be raised.
        """
        if not self.__is_connected:
            raise UserWarning("The client is not connected to server.\nConnect to server before send payload.")
        try:
            self.__socket.send(payload)
            glog.debug("Payload sent to server: " + payload.decode(self.__encoding))
        except socket.error:
            raise socket.error("Failed to send payload to server") from None
    def receive(self):
        try:
            data = self.__socket.recv(self.__buffer_size)
            return data
        except socket.timeout:
            pass
        except socket.error as error:
            if error.errno == errno.ECONNRESET:
                self.disconnect()
        return None


    def start_receive(self, on_received = None):
        """Start receive loop.
        Args:
            on_received: Receive callback for get received data. On None received data will be printed to stdout. Default: None.
        Raises:
            UserWarning: If client is not connected to server or if receive loop is already running this will be raised.
        """
        if not self.__is_connected:
            raise UserWarning("The client is not connected to server.\nConnect to server before start loop.")
        elif self.__is_receiving:
            raise UserWarning("Receive loop is already running.")
        self.__is_receiving = True
        self.__loop = threading.Thread(target = self.__receive_loop, args = (on_received,))
        self.__loop.start()
        glog.debug("Receive loop started")
    def stop_receive(self):
        """Stop receive loop.
        Returns:
            True if stop receive loop is successful, False otherwise.
        """
        if not self.__is_receiving:
            return False
        self.__is_receiving = False
        self.__loop.join(timeout = self.__timeout)
        self.__loop = None
        glog.debug("Receive loop stopped")
        return True
        
    # Private functions
    def __receive_loop(self, on_received = None):
        """Loop to receive payload from server.
        Args:
            on_received: Receive callback for get received data. On None received data will be printed to stdout. Default: None.
        """
        while self.__is_connected and self.__is_receiving:
            data = self.receive()
            if self.__is_receiving and data and len(data) > 1:
                if on_received is None:
                    print(data.decode(self.__encoding))
                else:
                    on_received(data)
        

if __name__ == "__main__":
    if not DEBUG_MODE:
        sys.tracebacklimit = 0
        glog.setLevel("INFO")
    else:
        glog.setLevel("DEBUG")

    parser = argparse.ArgumentParser()
    parser.add_argument('Address', type=str, help="Adress or hostname of tcp server")
    parser.add_argument('Port', type=int, help="Port of tcp server")
    parser.add_argument('-s', '--size', type=int, help="Receive buffer size")
    parser.add_argument('-t', '--timeout', type=int, help="Timeout of tcp connection and receive")
    parser.add_argument('-e', '--encoding', type=str, help="Encoding that will used in tcp communication")
    args = parser.parse_args()

    kb = KBHit.KBHit()

    tcp_client = TcpClient()
    if args.size is not None:
        tcp_client.set_buffer_size(args.size)
    if args.timeout is not None:
        tcp_client.set_timeout(args.timeout)
    if args.encoding is not None:
        try:
            codecs.lookup(args.encoding)
            tcp_client.set_encoding(args.encoding)
        except LookupError:
            raise LookupError('Unkown encoding: ' + args.encoding) from None
    
    tcp_client.connect(args.Address, args.Port, True)
    glog.info("Connected to server. Press ESC or CTRL+C to quit")

    encoding = tcp_client.get_encoding()
    payload = ""
    while tcp_client.is_connected():
        try:
            input = kb.getch()
            keycode = ord(input)

            if keycode == 27:
                glog.info("ESC pressed. Disconnecting from server...")
                tcp_client.disconnect()
                break
            elif keycode == 10:
                tcp_client.send(payload.encode(encoding))
                payload = ""
                print()
            elif keycode == 127:
                payload = payload[:-1]
                print('\b', end="", flush=True)
            else:
                payload += input
                print(input, end="", flush=True)
        except KeyboardInterrupt:
            glog.info("CTRL+C pressed. Disconnecting from server...")
            tcp_client.disconnect()
            break
    kb.set_normal_term()
        
        
            
    
    