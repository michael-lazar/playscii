import math
import numpy as np
import vector

def clamp(val, lowest, highest):
    return min(highest, max(lowest, val))

class Camera:
    
    # good starting values
    start_x,start_y = 0,0
    start_zoom = 2.5
    x_tilt, y_tilt = 0, 0
    # pan/zoom speed tuning
    mouse_pan_rate = 10
    pan_accel = 0.005
    base_max_pan_speed = 0.8
    pan_friction = 0.1
    # min/max zoom % between which pan speed variation scales
    pan_min_pct = 25.0
    pan_max_pct = 200.0
    # factor by which zoom level modifies pan speed
    pan_zoom_increase_factor = 16
    zoom_accel = 0.1
    max_zoom_speed = 2.5
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
        self.max_pan_speed = self.base_max_pan_speed
    
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
        up = vector.Vec3(0, 1, 0)
        target = vector.Vec3(eye.x + self.x_tilt, eye.y + self.y_tilt, 0)
        # view axes
        forward = (target - eye).normalize()
        side = forward.cross(up).normalize()
        upward = side.cross(forward)
        m = [[side.x, upward.x, -forward.x, 0],
             [side.y, upward.y, -forward.y, 0],
             [side.z, upward.z, -forward.z, 0],
             [-eye.dot(side), -eye.dot(upward), eye.dot(forward), 1]]
        self.view_matrix = np.array(m, dtype=np.float32)
        self.look_x, self.look_y, self.look_z = side, upward, forward
    
    def get_perspective_matrix(self):
        zmul = (-2 * self.near_z * self.far_z) / (self.far_z - self.near_z)
        ymul = 1 / math.tan(self.fov * math.pi / 360)
        aspect = self.app.window_width / self.app.window_height
        xmul = ymul / aspect
        m = [[xmul,    0,    0,  0],
             [   0, ymul,    0,  0],
             [   0,    0,   -1, -1],
             [   0,    0, zmul,  0]]
        return np.array(m, dtype=np.float32)
    
    def get_ortho_matrix(self, width=None, height=None):
        width, height = width or self.app.window_width, height or self.app.window_height
        m = np.eye(4, 4, dtype=np.float32)
        left, bottom = 0, 0
        right, top = width, height
        far_z, near_z = -1, 1
        x = 2 / (right - left)
        y = 2 / (top - bottom)
        z = -2 / (self.far_z - self.near_z)
        wx = -(right + left) / (right - left)
        wy = -(top + bottom) / (top - bottom)
        wz = -(self.far_z + self.near_z) / (self.far_z - self.near_z)
        m = [[ x,  0,  0, 0],
             [ 0,  y,  0, 0],
             [ 0,  0,  z, 0],
             [wx, wy, wz, 0]]
        return np.array(m, dtype=np.float32)
    
    def pan(self, dx, dy, keyboard=False):
        # modify pan speed based on zoom according to a factor
        m = (self.pan_zoom_increase_factor * self.z) / self.min_zoom
        self.vel_x += dx * self.pan_accel * m
        self.vel_y += dy * self.pan_accel * m
        # for brevity, app passes in whether user appears to be keyboard editing
        if keyboard:
            self.app.keyboard_editing = True
    
    def zoom(self, dz, keyboard=False, towards_cursor=False):
        self.vel_z += dz * self.zoom_accel
        # pan towards cursor while zooming?
        if towards_cursor:
            dx = self.app.cursor.x - self.x
            dy = self.app.cursor.y - self.y
            self.pan(dx, dy, keyboard)
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
        self.app.ui.active_art.camera_zoomed_extents = False
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
    
    def find_closest_zoom_extents(self):
        def corners_on_screen():
            art = self.app.ui.active_art
            z = art.layers_z[-1]
            x1, y1 = art.renderables[0].x, art.renderables[0].y
            left, top = vector.world_to_screen_normalized(self.app, x1, y1, z)
            x2 = x1 + art.width * art.quad_width
            y2 = y1 - art.height * art.quad_height
            right, bot = vector.world_to_screen_normalized(self.app, x2, y2, z)
            #print('(%.3f, %.3f) -> (%.3f, %.3f)' % (left, top, right, bot))
            # add 1 tile of UI chars to top and bottom margins
            top_margin = 1 - self.app.ui.menu_bar.art.quad_height
            bot_margin = -1 + self.app.ui.status_bar.art.quad_height
            return left >= -1 and top <= top_margin and \
                right <= 1 and bot >= bot_margin
        # zoom out from minimum until all corners are visible
        self.z = self.min_zoom
        # recalc view matrix each move so projection stays correct
        self.calc_view_matrix()
        tries = 0
        while not corners_on_screen() and tries < 30:
            self.zoom_proportional(-1)
            self.calc_view_matrix()
            tries += 1
    
    def toggle_zoom_extents(self, override=None):
        art = self.app.ui.active_art
        if override is not None:
            art.camera_zoomed_extents = not override
        if art.camera_zoomed_extents:
            # restore cached position
            self.x, self.y, self.z = art.non_extents_camera_x, art.non_extents_camera_y, art.non_extents_camera_z
        else:
            art.non_extents_camera_x, art.non_extents_camera_y, art.non_extents_camera_z = self.x, self.y, self.z
            # center camera on art
            self.x = (art.width * art.quad_width) / 2
            self.y = -(art.height * art.quad_height) / 2
            self.find_closest_zoom_extents()
        # kill all camera velocity when snapping
        self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
        art.camera_zoomed_extents = not art.camera_zoomed_extents
    
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
        # zoom-proportional pan scale is based on art
        if self.app.ui.active_art:
            speed_scale = clamp(self.get_current_zoom_pct(),
                                self.pan_min_pct, self.pan_max_pct)
            self.max_pan_speed = self.base_max_pan_speed / (speed_scale / 100)
        else:
            self.max_pan_speed = self.base_max_pan_speed
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
            if self.app.ui.active_art and (self.vel_x or self.vel_y):
                self.app.ui.active_art.camera_zoomed_extents = False
            # move
            self.x += self.vel_x
            self.y += self.vel_y
        # process Z separately
        self.vel_z = clamp(self.vel_z, -self.max_zoom_speed, self.max_zoom_speed)
        self.vel_z *= 1 - self.zoom_friction
        if abs(self.vel_z) < self.min_velocity:
            self.vel_z = 0
        # as bove, if zooming turn off zoom-extents state
        if self.vel_z and self.app.ui.active_art:
            self.app.ui.active_art.camera_zoomed_extents = False
        self.z += self.vel_z
        # keep within bounds
        if self.use_bounds:
            self.x = clamp(self.x, self.min_x, self.max_x)
            self.y = clamp(self.y, self.min_y, self.max_y)
            self.z = clamp(self.z, self.min_zoom, self.max_zoom)
        # set view matrix from xyz
        self.calc_view_matrix()
        self.moved_this_frame = self.mouse_panned or self.x != self.last_x or self.y != self.last_y or self.z != self.last_z
        self.mouse_panned = False
    
    def log_loc(self):
        self.app.log('camera x=%s, y=%s, z=%s' % (self.x, self.y, self.z))
