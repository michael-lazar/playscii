import math
import numpy as np

from OpenGL import GL, GLU

class Vec3:
    
    "Basic 3D vector class. Not used very much currently."
    
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
    
    def __str__(self):
        return 'Vec3 %.4f, %.4f, %.4f' % (self.x, self.y, self.z)
    
    def __sub__(self, b):
        "Return a new vector subtracted from given other vector."
        return Vec3(self.x - b.x, self.y - b.y, self.z - b.z)
    
    def length(self):
        "Return this vector's scalar length."
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)
    
    def normalize(self):
        "Return a unit length version of this vector."
        n = Vec3()
        l = self.length()
        if l != 0:
            ilength = 1.0 / l
            n.x = self.x * ilength
            n.y = self.y * ilength
            n.z = self.z * ilength
        return n
    
    def cross(self, b):
        "Return a new vector of cross product with given other vector."
        x = self.y * b.z - self.z * b.y
        y = self.z * b.x - self.x * b.z
        z = self.x * b.y - self.y * b.x
        return Vec3(x, y, z)
    
    def dot(self, b):
        "Return scalar dot product with given other vector."
        return self.x * b.x + self.y * b.y + self.z * b.z
    
    def inverse(self):
        "Return a new vector that is inverse of this vector."
        return Vec3(-self.x, -self.y, -self.z)
    
    def copy(self):
        "Return a copy of this vector."
        return Vec3(self.x, self.y, self.z)

def get_tiles_along_line(x0, y0, x1, y1):
    """
    Return list of (x,y) tuples for all tiles crossing given line points
    """
    tiles = []
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return [(x0, y0)]
    elif dx == 0:
        for y in range(y0, y1):
            tiles.append((x0, y))
        return tiles
    # Bresenham's line algorithm
    delta_error = abs(float(dy) / dx)
    error = 0.
    y = y0
    for x in range(x0, x1):
        tiles.append((x, y))
        error += delta_error
        while error >= 0.5:
            y += 1 if dy >= 0 else -1
            error -= 1.0
    # include end point tile, algo stops short of it
    tiles.append((x1, y1))
    return tiles

def cut_xyz(x, y, z, threshold):
    """
    Return input x,y,z with each axis clamped to 0 if it's close enough to
    given threshold
    """
    x = x if abs(x) > threshold else 0
    y = y if abs(y) > threshold else 0
    z = z if abs(z) > threshold else 0
    return x, y, z

def ray_plane_intersection(plane_x, plane_y, plane_z,
                           plane_dir_x, plane_dir_y, plane_dir_z,
                           ray_x, ray_y, ray_z,
                           ray_dir_x, ray_dir_y, ray_dir_z):
    # from http://stackoverflow.com/a/39424162
    plane = np.array([plane_x, plane_y, plane_z])
    plane_dir = np.array([plane_dir_x, plane_dir_y, plane_dir_z])
    ray = np.array([ray_x, ray_y, ray_z])
    ray_dir = np.array([ray_dir_x, ray_dir_y, ray_dir_z])
    ndotu = plane_dir.dot(ray_dir)
    if abs(ndotu) < 0.000001:
        #print ("no intersection or line is within plane")
        return 0, 0, 0
    w = ray - plane
    si = -plane_dir.dot(w) / ndotu
    psi = w + si * ray_dir + plane
    return psi[0], psi[1], psi[2]

def screen_to_world(app, screen_x, screen_y):
    """
    Return 3D (float) world space coordinates for given 2D (int) screen space
    coordinates.
    """
    # thanks http://www.bfilipek.com/2012/06/select-mouse-opengl.html
    # get world space ray from view space mouse loc
    screen_y = app.window_height - screen_y
    z1, z2 = 0, 0.99999
    pjm = np.matrix(app.camera.projection_matrix, dtype=np.float64)
    vm = np.matrix(app.camera.view_matrix, dtype=np.float64)
    start_x, start_y, start_z = GLU.gluUnProject(screen_x, screen_y, z1, vm, pjm)
    end_x, end_y, end_z = GLU.gluUnProject(screen_x, screen_y, z2, vm, pjm)
    dir_x, dir_y, dir_z = end_x - start_x, end_y - start_y, end_z - start_z
    # define Z of plane to test against
    # TODO: what Z is appropriate for game mode picking? test multiple planes?
    art = app.ui.active_art
    plane_z = art.layers_z[art.active_layer] if art and not app.game_mode else 0
    x, y, z = ray_plane_intersection(0, 0, plane_z, # plane loc
                                     0, 0, 1, # plane dir
                                     end_x, end_y, end_z, # ray origin
                                     dir_x, dir_y, dir_z) # ray dir
    return x, y, z

def world_to_screen(app, world_x, world_y, world_z):
    """
    Return 2D screen pixel space coordinates for given 3D (float) world space
    coordinates.
    """
    pjm = np.matrix(app.camera.projection_matrix, dtype=np.float64)
    vm = np.matrix(app.camera.view_matrix, dtype=np.float64)
    # viewport tuple order should be same as glGetFloatv(GL_VIEWPORT)
    viewport = (0, 0, app.window_width, app.window_height)
    try:
        x, y, z = GLU.gluProject(world_x, world_y, world_z, vm, pjm, viewport)
    except:
        x, y, z = 0, 0, 0
        app.log('GLU.gluProject failed!')
    # does Z mean anything here?
    return x, y

def world_to_screen_normalized(app, world_x, world_y, world_z):
    """
    Return normalized (-1 to 1) 2D screen space coordinates for given 3D
    world space coordinates.
    """
    x, y = world_to_screen(app, world_x, world_y, world_z)
    x = (2 * x) / app.window_width - 1
    y = (-2 * y) / app.window_height + 1
    return x, -y
