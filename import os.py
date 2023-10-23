import os
import socket
import struct
import time
import select
import sys

ICMP_ECHO_REQUEST = 8

def checksum(msg):
    s = 0
    n = len(msg)
    for i in range(0, n, 2):
        s += msg[i + 1] * 256 + msg[i]
    s = (s >> 16) + (s & 0xffff)
    s += s >> 16
    return ~s & 0xffff

def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout
    while True:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = time.time() - startedSelect
        if whatReady[0] == []:  # Timeout
            return "Request timed out."
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fetch the ICMP header from the IP packet
        icmpHeader = recPacket[20:28]
        type, code, checksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader)
        if type == 0 and packetID == ID:
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
            return timeReceived - timeSent

        timeLeft -= howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
    myChecksum = 0
    # Make a dummy header with a 0 checksum
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)
    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        myChecksum = socket.htons(myChecksum) & 0xffff
    else:
        myChecksum = socket.htons(myChecksum) & 0xffff
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

def doOnePing(destAddr, timeout):
    icmp = socket.getprotobyname("icmp")
    mySocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    myID = os.getpid() & 0xFFFF  # Return the current process ID
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay

def ping(host, timeout=1):
    dest = host
    print(f"Pinging {dest} with 32 bytes of data:")
    delay = doOnePing(dest, timeout)
    if isinstance(delay, str):
        print(delay)
    else:
        print(f"Reply from {dest}: bytes=32 time={int(delay * 1000)}ms TTL=64")

# Example Usage - Pinging localhost
ping("127.0.0.1")
