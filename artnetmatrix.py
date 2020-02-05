import numpy, sys
from artnetbroadcaster import ArtNetBroadcaster
from artnetreceiver import ArtNetReceiver

LEDS_PER_PIXEL = 3  # This would change if RGBW were supported
MAX_CHANNEL = 511  # for zero based channels
DEFAULT_BRIGHTNESS = 64
MAX_BRIGHTNESS = 128

START_PIXEL_TOP = 0x00  # Pixel 0 is at top of matrix
START_PIXEL_BOTTOM = 0x01  # Pixel 0 is at bottom of matrix
START_PIXEL_LEFT = 0x00  # Pixel 0 is at left of matrix
START_PIXEL_RIGHT = 0x02  # Pixel 0 is at right of matrix
MASK_START_PIXEL = 0x03

DIRECTION_ROWS = 0x00  # Matrix is row major (horizontal)
DIRECTION_COLUMNS = 0x04  # Matrix is column major (vertical)
MASK_DIRECTION = 0x04

LAYOUT_PROGRESSIVE = 0x00  # Each line flows in the same direction
LAYOUT_SNAKE = 0x08  # Pixel order reverses from line to line
MASK_LAYOUT = 0x08

COLOR_ORDER_RGB = 0

MATRIX_MODE_BROADCAST = 0x00
MATRIX_MODE_RECEIVE = 0x01


class PixelMap:
    """
    pixel_map = [
        [
            [universe,start_channel],
            [universe,start_channel],
            [universe,start_channel]
        ],  # row 1
        [
            [universe,start_channel],
            [universe,start_channel],
            [universe,start_channel]
        ],  # row 2
        [
            [universe,start_channel],
            [universe,start_channel],
            [universe,start_channel]
        ],  # row 3

    ]
    """

    mapping = []

    def __init__(
        self,
        dimensions,
        start_pixel=0,
        layout=LAYOUT_SNAKE,
        direction=DIRECTION_COLUMNS,
        start_channel=0,
        start_universe=0,
        color_order=COLOR_ORDER_RGB,
    ):
        print("making mapping")
        if not color_order == COLOR_ORDER_RGB:
            raise ValueError("only rgb color order supported currently")

        if not (direction == DIRECTION_COLUMNS):
            raise ValueError("only columnwise currently supported")

        shape = dimensions[::-1]
        self.mapping = numpy.zeros(shape + (2,))

        max_x, max_y = (i - 1 for i in dimensions)
        # x, y = 0, max_y  #bottom left
        if start_pixel & START_PIXEL_BOTTOM:
            y = max_y
            y_dir = -1
        else:
            y = 0
            y_dir = 1

        if start_pixel & START_PIXEL_RIGHT:
            x = max_x
            x_dir = -1
        else:
            x = 0
            x_dir = 1

        current_channel = start_channel
        current_universe = start_universe
        while x >= 0 if x_dir < 0 else x <= max_x:
            while y >= 0 if y_dir < 0 else y <= max_y:
                self.mapping[y][x] = (current_universe, current_channel)
                current_channel += LEDS_PER_PIXEL
                if (current_channel + (LEDS_PER_PIXEL - 1)) > MAX_CHANNEL:
                    current_channel = start_channel
                    current_universe += 1

                y = y - 1 if (y_dir < 0) else y + 1

            if layout == LAYOUT_SNAKE:
                y_dir *= -1
            else:
                y = max_y if start_pixel & START_PIXEL_BOTTOM else 0

            y = 0 if y_dir > 0 else max_y
            x = x - 1 if (x_dir < 0) else (x + 1)
        print(self.mapping)


class ArtNetMatrix:
    matrix_config = 0x00
    offset_rgb = [0, 1, 2]  # RGB target
    mode = MATRIX_MODE_BROADCAST
    # will have to change to others if, say GRB were supported
    # offset_rgb = [1,0,2]

    start_universe = 0
    start_channel = 0

    surface = None

    """
    # to get correct output:
       [r,g,b] = buffer[y][x]
       [universe, start_channel] = pixel_map_actual[y][x]
       universes[universe][start_channel][offset_rgb[0]] = r
       universes[universe][start_channel][offset_rgb[1]] = g
       universes[universe][start_channel][offset_rgb[2]] = b
    """

    def __init__(self, dimensions, matrix_config, color_order):
        self._broadcaster = None
        self._surface = None
        self.brightness = DEFAULT_BRIGHTNESS
        self.dimensions = dimensions
        # reverse for our arrays which are indexed by y,x, not x,y
        self.shape = dimensions[::-1]
        self.matrix_config = matrix_config
        self.color_order = color_order
        self._create_pixel_map()

    def setReceiveMode(self, receiver):
        self.mode = MATRIX_MODE_RECEIVE
        self.receiver = receiver

    @property
    def broadcaster(self):
        if self._broadcaster is None:
            self._broadcaster = ArtNetBroadcaster()
        return self._broadcaster

    @property
    def surface(self):
        if self._surface is None:
            self._surface = numpy.zeros(self.shape + (LEDS_PER_PIXEL,)).astype("uint8")
        return self._surface

    def setBrightness(self, brightness):
        self.brightness = min(brightness, MAX_BRIGHTNESS)

    def fill(self, color):
        self.surface[:] = color

    def clear(self):
        return self.fill((0, 0, 0))

    def unpack_universes(self, universes):
        """ Takes a dict of universe -> bytearray, and a pixel map and fills
            a surface area w/ the correct colors. returns [x][y][rgb] surface
            array
        """
        outputsurface = numpy.zeros(self.shape + (LEDS_PER_PIXEL,)).astype("uint8")

        roff, goff, boff = self.offset_rgb

        # this is probably a better way, but whatev
        # for universe, data in universes:

        for y, x in numpy.ndindex(self.shape):
            universe, start_channel = [int(i) for i in self.pixelMap.mapping[y, x]]

            # TODO: take roff, boff, goff into account to reorder colors to rgb
            c1, c2, c3 = universes[universe][
                start_channel : start_channel + LEDS_PER_PIXEL
            ]

            outputsurface[y, x] = c3, c2, c1

        return outputsurface

    def prepare_universes(self):
        """ Takes the surface object and a pixel map and creates output
            buffers, one for each universe, containing pixel data
        """
        max_universe = self.pixelMap.mapping[:, :, 0].max()
        universe_buffers = numpy.zeros((int(max_universe + 1), 512))
        roff, goff, boff = self.offset_rgb
        scaler = min(self.brightness, MAX_BRIGHTNESS) / 255
        # just make all colors scale the same for now
        scaleg, scaleb = [scaler, scaler]

        for y, x in numpy.ndindex(self.shape):
            r, g, b = self.surface[y, x]
            universe, start_channel = [int(i) for i in self.pixelMap.mapping[y, x]]
            universe_buffers[universe][start_channel + roff] = int(r * scaler)
            universe_buffers[universe][start_channel + goff] = int(g * scaleg)
            universe_buffers[universe][start_channel + boff] = int(b * scaleb)
            # TODO: there's probably some better numpy syntax for this, like:
            # universe_buffers[universe][start_ch:start_ch+LEDS_PER_PIXEL]
        return universe_buffers

    def _create_pixel_map(self):
        self.pixelMap = PixelMap(
            self.dimensions,
            start_pixel=self.matrix_config & MASK_START_PIXEL,
            layout=self.matrix_config & MASK_LAYOUT,
        )

    def receiveFrame(self):
        if self.mode != MATRIX_MODE_RECEIVE:
            raise TypeError("Matrix is not in receive mode")
        universes = {}
        max_universe = self.pixelMap.mapping[:, :, 0].max()

        while len(universes.keys()) <= max_universe:
            packet = self.receiver.receive()
            if packet:
                # if len(u_c.keys()) < 3:
                # print(packet.data[0:2])
                # else:
                #    return
                universes[packet.universe] = packet.data
        return self.unpack_universes(universes)

    def update(self):
        """ Sends the surface out over the wire if we are in broadcase mode """
        if self.mode != MATRIX_MODE_BROADCAST:
            raise TypeError("Matrix is not in broadcast mode")

        for i, data in enumerate(self.prepare_universes()):
            self.broadcaster.send(data, i)
