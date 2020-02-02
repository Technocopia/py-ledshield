import numpy
from artnet import ArtNetBroadcaster

LEDS_PER_PIXEL = 3 # This would change if RGBW were supported
MAX_CHANNEL = 511 #for zero based channels
DEFAULT_BRIGHTNESS = 64
MAX_BRIGHTNESS = 128

START_PIXEL_TOP = 0x00 # Pixel 0 is at top of matrix
START_PIXEL_BOTTOM = 0x01 # Pixel 0 is at bottom of matrix
START_PIXEL_LEFT = 0x00 # Pixel 0 is at left of matrix
START_PIXEL_RIGHT = 0x02 # Pixel 0 is at right of matrix
MASK_START_PIXEL = 0x03

DIRECTION_ROWS = 0x00 # Matrix is row major (horizontal)
DIRECTION_COLUMNS = 0x04 # Matrix is column major (vertical)
MASK_DIRECTION = 0x04

LAYOUT_PROGRESSIVE = 0x00 # Each line flows in the same direction
LAYOUT_SNAKE = 0x08 # Pixel order reverses from line to line
MASK_LAYOUT = 0x08

COLOR_ORDER_RGB = 0

class ArtNetMatrix(object):
    matrix_config = 0x00

    offset_rgb = [0,1,2] #RGB target
    # offset_rgb = [1,0,2] #will have to change to others if, say GRB were supported

    start_universe = 0
    start_channel = 0

    surface = None

    """
    pixel_map = [
        [[universe,start_channel],[universe,start_channel],[universe,start_channel]],  # row 1
        [[universe,start_channel],[universe,start_channel],[universe,start_channel]],  # row 2
        [[universe,start_channel],[universe,start_channel],[universe,start_channel]],  # row 3
    ]
    """

    """
    # to get correct output:
       [r,g,b] = buffer[y][x]
       [universe, start_channel] = pixel_map_actual[y][x]
       universes[universe][start_channel][offset_rgb[0]] = r
       universes[universe][start_channel][offset_rgb[1]] = g
       universes[universe][start_channel][offset_rgb[2]] = b
    """
    def __init__(self, dimensions, matrix_config, color_order):
        self._artnet = None
        self._surface = None
        self.brightness = DEFAULT_BRIGHTNESS
        self.dimensions = dimensions
        self.shape = dimensions[::-1] # reverse for our arrays which are indexed by y,x, not x,y
        self.matrix_config = matrix_config
        self.color_order = color_order
        self._create_pixel_map()

    @property
    def artnet(self):
        if self._artnet is None:
            self._artnet = ArtNet()
        return self._artnet

    @property
    def surface(self):
        if self._surface is None:
            self._surface = numpy.zeros(self.shape + (LEDS_PER_PIXEL,)).astype('uint8')
        return self._surface

    def setBrightness(self, brightness):
        self.brightness = min(brightness, MAX_BRIGHTNESS)

    def fill(self, color):
        self.surface[:] = color

    def clear(self):
        return self.fill((0,0,0))

    def prepare_universes(self):
        max_universe = self.pixel_map[:,:,0].max()
        universe_buffers = numpy.zeros((int(max_universe+1), 512))
        roff, goff, boff = self.offset_rgb
        scaler = min(self.brightness,MAX_BRIGHTNESS)/255
        scaleg, scaleb = [scaler, scaler] #just make all colors scale the same for now

        for y,x in numpy.ndindex(self.shape):
            r,g,b = self.surface[y, x]
            universe, start_channel = [int(i) for i in self.pixel_map[y,x]]
            universe_buffers[universe][start_channel + roff] = int(r*scaler)
            universe_buffers[universe][start_channel + goff] = int(g*scaleg)
            universe_buffers[universe][start_channel + boff] = int(b*scaleb)
            #TODO: there's probably some better numpy syntax for this, like so:
            #universe_buffers[universe][start_channel:start_channel+LEDS_PER_PIXEL]
        return universe_buffers

    def update(self):
        for i,data in enumerate(self.prepare_universes()):
            self.artnet.send(data, i)

    def _create_pixel_map(self):
        if not self.color_order == COLOR_ORDER_RGB:
            raise ValueError("only rgb color order supported currently")
        start_pixel = self.matrix_config & MASK_START_PIXEL
        if not (start_pixel == (START_PIXEL_BOTTOM | START_PIXEL_LEFT)):
            raise ValueError("only bottom left supported at the moment")
        layout = self.matrix_config & MASK_LAYOUT
        if not (layout == LAYOUT_SNAKE):
            raise ValueError("only snake layout currently supported")

        self.pixel_map = numpy.zeros(self.shape + (2,))

        max_x,max_y = (i-1 for i in self.dimensions)
        x, y = 0, max_y # starting bottom left
        x_dir, y_dir = 1, -1 #starting bottom left
        current_channel = self.start_channel
        current_universe = self.start_universe
        while x >= 0 if x_dir < 0 else x <= max_x:
            while y >= 0 if y_dir < 0 else y <= max_y:
                self.pixel_map[y][x] = (current_universe, current_channel)
                current_channel += LEDS_PER_PIXEL
                if(current_channel + (LEDS_PER_PIXEL-1)) > MAX_CHANNEL:
                    current_channel=self.start_channel
                    current_universe+=1

                y = y-1 if (y_dir < 0) else y+1

            y_dir *= -1
            y = 0 if y_dir > 0 else max_y
            x = x-1 if (x_dir < 0) else (x+1)
