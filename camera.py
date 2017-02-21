import math
import numpy as np
import vector

def clamp(val, lowest, highest):
    return min(highest, max(lowest, val))

class Camera:
    
    # debug log camera values
    logg = False
    # good starting values
    start_x,start_y = 0,0
    start_zoom = 2.5
    x_tilt, y_tilt = 0, 0
    # pan/zoom speed tuning
    mouse_pan_rate = 10
    pan_accel = 0.005
    max_pan_speed = 0.4
    pan_friction = 0.1
    # factor by which zoom level modifies pan speed
    pan_zoom_increase_factor = 2
    zoom_accel = 0.03
    max_zoom_speed = 0.5
    zoom_friction = 0.1
    # kill velocity if below this
    min_velocity = 0.05
    # map extents
    # starting values only, bounds are generated according to art size
    min_x,max_x = 0, 50
    min_y,max_y = -50, 0
    use_bounds = True
    min_zoom,max_zoom = 1, 1000
    # matrices -> worldspace renderable vertex shader uniforms
    fov = 90
    near_z = 0.0001
    far_z = 100000
    
    def __init__(self, app):
        self.app = app
        self.reset()
        # set True when "zoom extents" toggles on
        self.zoomed_extents = False
        self.saved_x, self.saved_y, self.saved_z = 0, 0, self.start_zoom
    
    def reset(self):
        self.x, self.y = self.start_x, self.start_y
        self.z = self.start_zoom
        # store look vectors so world/screen space conversions can refer to it
        self.look_x, self.look_y, self.look_z = None,None,None
        self.vel_x, self.vel_y, self.vel_z = 0,0,0
        self.mouse_panned, self.moved_this_frame = False, False
        # GameObject to focus on
        self.focus_object = None
        self.calc_projection_matrix()
        self.calc_view_matrix()
    
    def calc_projection_matrix(self):
        self.projection_matrix = self.get_perspective_matrix()
    
    def calc_view_matrix(self):
        eye = vector.Vec3(self.x, self.y, self.z)
        target = eye.copy()
        target.z = 0
        target.x += self.x_tilt
        target.y += self.y_tilt # camera pitch mode7 radness
        up = vector.Vec3(0, 1, 0)
        #self.view_matrix = matrix.look_at(loc, target, up)
        # http://stackoverflow.com/questions/21830340/understanding-glmlookat
        look_z = eye - target
        look_z = look_z.normalize()
        look_y = up
        look_x = look_y.cross(look_z)
        # recalc Y vector
        look_y = look_z.cross(look_x)
        # normalize all
        look_x = look_x.normalize()
        look_y = look_y.normalize()
        # turn into a matrix
        m = np.eye(4, 4, dtype=np.float32)
        m[0][0] = look_x.x
        m[1][0] = look_x.y
        m[2][0] = look_x.z
        m[3][0] = -look_x.dot(eye)
        m[0][1] = look_y.x
        m[1][1] = look_y.y
        m[2][1] = look_y.z
        m[3][1] = -look_y.dot(eye)
        m[0][2] = look_z.x
        m[1][2] = look_z.y
        m[2][2] = look_z.z
        m[3][2] = -look_z.dot(eye)
        m[0][3] = 0
        m[1][3] = 0
        m[2][3] = 0
        m[3][3] = 1
        self.look_x, self.look_y, self.look_z = look_x, look_y, look_z
        self.view_matrix = m
    
    def get_perspective_matrix(self):
        # https://github.com/g-truc/glm/blob/master/glm/gtc/matrix_transform.inl
        aspect = self.app.window_width / self.app.window_height
        assert(aspect != 0)
        assert(self.far_z != self.near_z)
        rad = math.radians(self.fov)
        tan_half_fov = math.tan(rad / 2)
        m = np.eye(4, 4, dtype=np.float32)
        m[0][0] = 1 / (aspect * tan_half_fov)
        m[1][1] = 1 / tan_half_fov
        m[2][2] = -(self.far_z + self.near_z) / (self.far_z - self.near_z)
        m[2][3] = -1
        m[3][2] = -(2 * self.far_z * self.near_z) / (self.far_z - self.near_z)
        m[3][3] = 0
        return m
    
    def get_ortho_matrix(self, width=None, height=None):
        width, height = width or self.app.window_width, height or self.app.window_height
        m = np.eye(4, 4, dtype=np.float32)
        left, bottom = 0, 0
        right, top = width, height
        far_z, near_z = -1, 1
        m[0][0] = 2 / (right - left)
        m[1][1] = 2 / (top - bottom)
        m[2][2] = -2 / (self.far_z - self.near_z)
        m[3][0] = -(right + left) / (right - left)
        m[3][1] = -(top + bottom) / (top - bottom)
        m[3][2] = -(self.far_z + self.near_z) / (self.far_z - self.near_z)
        return m
    
    def pan(self, dx, dy, keyboard=False):
        # modify pan speed based on zoom according to a factor
        m = ((1 * self.pan_zoom_increase_factor) * self.z) / self.min_zoom
        self.vel_x += dx * self.pan_accel * m
        self.vel_y += dy * self.pan_accel * m
        # for brevity, app passes in whether user appears to be keyboard editing
        if keyboard:
            self.app.keyboard_editing = True
    
    def zoom(self, dz, keyboard=False):
        self.vel_z += dz * self.zoom_accel
        if keyboard:
            self.app.keyboard_editing = True
    
    def get_current_zoom_pct(self):
        "returns % of base (1:1) for current camera"
        return (self.get_base_zoom() / self.z) * 100
    
    def get_base_zoom(self):
        "returns camera Z needed for 1:1 pixel zoom"
        wh = self.app.window_height
        ch = self.app.ui.active_art.charset.char_height
        # TODO: understand why this produces correct result for 8x8 charsets
        if ch == 8:
            ch = 16
        return wh / ch
    
    def set_to_base_zoom(self):
        self.z = self.get_base_zoom()
    
    def zoom_proportional(self, direction):
        "zooms in or out via increments of 1:1 pixel scales for active art"
        if not self.app.ui.active_art:
            return
        self.zoomed_extents = False
        base_zoom = self.get_base_zoom()
        # build span of all 1:1 zoom increments
        zooms = []
        m = 1
        while base_zoom / m > self.min_zoom:
            zooms.append(base_zoom / m)
            m *= 2
        zooms.reverse()
        m = 1
        while base_zoom * m < self.max_zoom:
            zooms.append(base_zoom * m)
            m *= 2
        # set zoom to nearest increment in direction we're heading
        if direction > 0:
            zooms.reverse()
            for zoom in zooms:
                if self.z > zoom:
                    self.z = zoom
                    break
        elif direction < 0:
            for zoom in zooms:
                if self.z < zoom:
                    self.z = zoom
                    break
        # kill all Z velocity for camera so we don't drift out of 1:1
        self.vel_z = 0
    
    def toggle_zoom_extents(self, override=None):
        if override is not None:
            self.zoomed_extents = not override
        if self.zoomed_extents:
            self.x, self.y, self.z = self.saved_x, self.saved_y, self.saved_z
        else:
            self.saved_x, self.saved_y, self.saved_z = self.x, self.y, self.z
            # TODO: more involved zoom-extents that picks the best zoom level
            self.set_to_base_zoom()
            # center camera on art
            art = self.app.ui.active_art
            self.x = (art.width * art.quad_width) / 2
            self.y = -(art.height * art.quad_height) / 2
        # kill all camera velocity when snapping
        self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
        self.zoomed_extents = not self.zoomed_extents
    
    def window_resized(self):
        self.calc_projection_matrix()
    
    def set_zoom(self, z):
        # TODO: set lerp target, clear if keyboard etc call zoom()
        self.z = z
    
    def set_loc(self, x, y, z):
        self.x, self.y, self.z = x, y, (z or self.z) # z optional
    
    def set_loc_from_obj(self, game_object):
        self.set_loc(game_object.x, game_object.y, game_object.z)
    
    def set_for_art(self, art):
        # set limits
        self.max_x = art.width * art.quad_width
        self.min_y = -art.height * art.quad_height
        # use saved pan/zoom
        self.set_loc(art.camera_x, art.camera_y, art.camera_z)
    
    def mouse_pan(self, dx, dy):
        "pan view based on mouse delta"
        if dx == 0 and dy == 0:
            return
        m = ((1 * self.pan_zoom_increase_factor) * self.z) / self.min_zoom
        m /= self.max_zoom
        self.x -= dx / self.mouse_pan_rate * m
        self.y += dy / self.mouse_pan_rate * m
        self.vel_x = self.vel_y = 0
        self.mouse_panned = True
    
    def update(self):
        # remember last position to see if it changed
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
        # if focus object is set, use it for X and Y transforms
        if self.focus_object:
            # track towards target
            # TODO: revisit this for better feel later
            dx, dy = self.focus_object.x - self.x, self.focus_object.y - self.y
            l = math.sqrt(dx ** 2 + dy ** 2)
            if l != 0 and l > 0.1:
                il = 1 / l
                dx *= il
                dy *= il
                self.x += dx * self.pan_friction
                self.y += dy * self.pan_friction
        else:
            # clamp velocity
            self.vel_x = clamp(self.vel_x, -self.max_pan_speed, self.max_pan_speed)
            self.vel_y = clamp(self.vel_y, -self.max_pan_speed, self.max_pan_speed)
            # apply friction
            self.vel_x *= 1 - self.pan_friction
            self.vel_y *= 1 - self.pan_friction        
            if abs(self.vel_x) < self.min_velocity:
                self.vel_x = 0
            if abs(self.vel_y) < self.min_velocity:
                self.vel_y = 0
            # if camera moves, we're not in zoom-extents state anymore
            if self.vel_x or self.vel_y:
                self.zoomed_extents = False
            # move
            self.x += self.vel_x
            self.y += self.vel_y
        # process Z separately
        self.vel_z = clamp(self.vel_z, -self.max_zoom_speed, self.max_zoom_speed)
        self.vel_z *= 1 - self.zoom_friction
        if abs(self.vel_z) < self.min_velocity:
            self.vel_z = 0
        # as bove, if zooming turn off zoom-extents state
        if self.vel_z:
            self.zoomed_extents = False
        self.z += self.vel_z
        # keep within bounds
        if self.use_bounds:
            self.x = clamp(self.x, self.min_x, self.max_x)
            self.y = clamp(self.y, self.min_y, self.max_y)
            self.z = clamp(self.z, self.min_zoom, self.max_zoom)
        # set view matrix from xyz
        self.calc_view_matrix()
        if self.logg:
            self.app.log('camera x=%s, y=%s, z=%s' % (self.x, self.y, self.z))
        self.moved_this_frame = self.mouse_panned or self.x != self.last_x or self.y != self.last_y or self.z != self.last_z
        self.mouse_panned = False
