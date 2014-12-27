

def clamp(val, lowest, highest):
    return min(highest, max(lowest, val))

class Camera:
    
    # debug log camera values
    logg = False
    # good starting values
    start_x,start_y = 0,0
    start_zoom = 2.5
    # pan/zoom speed tuning
    pan_accel = 0.01
    max_pan_speed = 0.2
    pan_friction = 0.1
    zoom_accel = 0.01
    max_zoom_speed = 0.5
    zoom_friction = 0.1
    # kill velocity if below this
    min_velocity = 0.001
    # map extents
    min_x,max_x = -25, 25
    min_y,max_y = -25, 25
    min_zoom,max_zoom = 0.5, 15
    
    def __init__(self, window_width, window_height):
        self.x, self.y = self.start_x, self.start_y
        self.z = self.start_zoom
        self.vel_x, self.vel_y, self.vel_z = 0,0,0
        self.window_width, self.window_height = window_width, window_height
        #self.calc_projection_matrix()
        #self.calc_view_matrix()
    
    def pan(self, dx, dy):
        self.vel_x += dx * self.pan_accel
        self.vel_y += dy * self.pan_accel
    
    def zoom(self, dz):
        self.vel_z += dz * self.zoom_accel
    
    def mouse_pan(self, dx, dy):
        "pan view based on mouse delta"
        # TODO: this feels pretty crappy atm, figure out a better way
        pan_speed = 2
        il = 1 / math.sqrt(dx ** 2 + dy ** 2)
        x = dx * il * pan_speed
        y = dy * il * pan_speed
        self.pan(-x, y)
    
    def update(self):
        # clamp velocity
        self.vel_x = clamp(self.vel_x, -self.max_pan_speed, self.max_pan_speed)
        self.vel_y = clamp(self.vel_y, -self.max_pan_speed, self.max_pan_speed)
        self.vel_z = clamp(self.vel_z, -self.max_zoom_speed, self.max_zoom_speed)
        # apply friction
        self.vel_x *= 1 - self.pan_friction
        self.vel_y *= 1 - self.pan_friction
        self.vel_z *= 1 - self.zoom_friction
        if abs(self.vel_x) < self.min_velocity:
            self.vel_x = 0
        if abs(self.vel_y) < self.min_velocity:
            self.vel_y = 0
        if abs(self.vel_z) < self.min_velocity:
            self.vel_z = 0
        # move
        self.x += self.vel_x
        self.y += self.vel_y
        self.z += self.vel_z
        # keep within bounds
        self.x = clamp(self.x, self.min_x, self.max_x)
        self.y = clamp(self.y, self.min_y, self.max_y)
        self.z = clamp(self.z, self.min_zoom, self.max_zoom)
        # set view matrix from xyz
        #self.calc_view_matrix()
        if self.logg:
            print('camera x=%s, y=%s, z=%s' % (self.x, self.y, self.z))
