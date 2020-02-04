import sys
import socket

from struct import pack, unpack

ARTNET_HEADER = b'Art-Net\x00'

def make_artnet_packet(raw_data):
    if unpack('!8s', raw_data[:8])[0] != ARTNET_HEADER:
        return None
    return ArtnetPacket(raw_data)

class ArtnetPacket:
    def __init__(self, raw_data):
        (
            self.opcode,
            self.ver,
            self.sequence,
            self.physical,
            self.universe,
            self.length
        ) = unpack('!HHBBHH', raw_data[8:18])
        self.universe = unpack("<H", pack(">H", self.universe))[0]

        self.data = unpack(
            '{0}s'.format(int(self.length)),
            raw_data[18:18+int(self.length)])[0]

    def __str__(self):
        return ("ArtNet packet:\n - opcode: {0}\n - version: {1}\n - "
                "sequence: {2}\n - physical: {3}\n - universe: {4}\n - "
                "length: {5}\n - data : {6}").format(
            self.opcode, self.ver, self.sequence, self.physical,
            self.universe, self.length, self.data)


class ArtNetReceiver:
    IP = "127.0.0.1"
    PORT = 6454

    def __init__(self, port=PORT, ip=IP):
        self._socket = None
        self.port = port
        self.ip = ip

    @property
    def socket(self):
        if self._socket is None:
            self._socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP
            )
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.ip, self.port))
        return self._socket

    def receive(self):
        data, addr = self.socket.recvfrom(1024)
        return make_artnet_packet(data)


if __name__ == "__main__":
    print("artnet listner")
    artnet = ArtNetReceiver(ip="192.168.0.122")
    u_c = {}
    while True:
        packet = artnet.receive()
        if packet:
            if(len(u_c.keys()) < 3):
                print(packet)
            else:
                sys.exit()
            u_c[packet.universe] = True
