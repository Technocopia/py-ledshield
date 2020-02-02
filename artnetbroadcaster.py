import socket
import struct
import numpy


class ArtNetBroadcaster:
    PORT = 6454  # 0x1936

    def __init__(self, port=PORT):
        self._socket = None
        self.port = port

    @property
    def socket(self):
        if self._socket is None:
            self._socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP
            )
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        return self._socket

    def new_packet(self, sequence=70, universe=0x03):
        packet = bytearray()
        packet.extend(map(ord, "Art-Net"))
        packet.append(0x00)          # Null terminate Art-Net
        packet.extend([0x00, 0x50])  # Opcode ArtDMX 0x5000 (Little endian)
        packet.extend([0x00, 0x0e])  # Protocol version 14
        packet.append(sequence)  # sequence #
        packet.append(0x00)  # Physical
        # Universe low/high
        packet.extend([universe & 0xFF, universe >> 8 & 0xFF])
        return packet

    def _make_message(self, data, universe):
        packet = self.new_packet(0, universe)
        highest_channel = len(data)
        # Pack the number of channels Big endian
        packet.extend(struct.pack('>h', highest_channel))
        packet.extend(numpy.uint8(data))
        return packet

    def send(self, data, universe):
        msg = self._make_message(data, universe)
        return self.socket.sendto(msg, ('<broadcast>', self.port))
