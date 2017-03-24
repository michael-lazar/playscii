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

def cut_xyz(x, y, z, threshold):
    """
    Return input x,y,z with each axis clamped to 0 if it's close enough to
    given threshold
    """
    x = x if abs(x) > threshold else 0
    y = y if abs(y) > threshold else 0
    z = z if abs(z) > threshold else 0
    return x, y, z

def transform_vec4(x, y, z, w, m):
    "Transform given 4D vector by given matrix."
    m = m.T
    #m = m.getA()
    out_x = x * m[0][0] + y * m[1][0] + z * m[2][0] + w * m[3][0]
    out_y = x * m[0][1] + y * m[1][1] + z * m[2][1] + w * m[3][1]
    out_z = x * m[0][2] + y * m[1][2] + z * m[2][2] + w * m[3][2]
    out_w = x * m[0][3] + y * m[1][3] + z * m[2][3] + w * m[3][3]
    return out_x, out_y, out_z, out_w

def unproject(screen_x, screen_y, screen_z, screen_width, screen_height,
              screen_projection_matrix, screen_view_matrix):
    """
    Return 4D vector unprojected using given screen dimensions and
    projection + view matrices.
    """
    x = 2 * screen_x / screen_width - 1
    y = -(2 * screen_y / screen_height + 1)
    z = screen_z
    w = 1.0
    inv_proj = np.linalg.inv(screen_projection_matrix)
    inv_view = np.linalg.inv(screen_view_matrix)
    x, y, z, w = transform_vec4(x, y, z, w, inv_proj)
    x, y, z, w = transform_vec4(x, y, z, w, inv_view)
    if w != 0:
        x /= w
        y /= w
        z /= w
    return x, y, z, w

def screen_to_ray(x, y, width, height, projection_matrix, view_matrix,
                  near, far):
    "Return a 3D ray (start + normal) for given point in 2D screen space."
    unproject_args = [x, y, near, width, height, projection_matrix, view_matrix]
    near_x, near_y, near_z, near_w = unproject(*unproject_args)
    unproject_args[2] = far
    far_x, far_y, far_z, far_w = unproject(*unproject_args)
    dir_x, dir_y, dir_z = far_x - near_x, far_y - near_y, far_z - near_z
    dir_length = math.sqrt(dir_x ** 2 + dir_y ** 2 + dir_z ** 2)
    if dir_length != 0:
        dir_inv_length = 1 / dir_length
        dir_x *= dir_inv_length
        dir_y *= dir_inv_length
        dir_z *= dir_inv_length
    else:
        dir_x = dir_y = dir_z = 0
    return near_x, near_y, near_z, dir_x, dir_y, dir_z

def line_plane_intersection(plane_x, plane_y, plane_z, plane_d,
                            start_x, start_y, start_z, end_x, end_y, end_z):
    """
    Return 3D point of intersection for given plane (3D normal + distance from
    origin) and given line (start and end 3D vector).
    """
    # http://paulbourke.net/geometry/pointlineplane/
    u = (plane_x * start_x) + (plane_y * start_y) + (plane_z * start_z) + plane_d
    u /= plane_x * (start_x - end_x) + plane_y * (start_y - end_y) + plane_z * (start_z - end_z)
    if u <= 0 or u > 1:
        return False, False, False
    x = u * start_x + (1 - u) * end_x
    y = u * start_y + (1 - u) * end_y
    z = u * start_z + (1 - u) * end_z
    return x, y, z

def _screen_to_world_NEW(app, screen_x, screen_y):
    #near, far = app.camera.near_z, app.camera.far_z
    near, far = 0, 1#app.camera.z
    args = (screen_x, screen_y, app.window_width, app.window_height,
            app.camera.projection_matrix, app.camera.view_matrix, near, far)
    start_x, start_y, start_z, ray_x, ray_y, ray_z = screen_to_ray(*args)
    # turn ray into line segment
    ray_dist = 100
    end_x = start_x + ray_x * ray_dist
    end_y = start_y + ray_y * ray_dist
    end_z = start_z + ray_z * ray_dist
    # determine "plane distance from origin"
    if app.ui.active_art and not app.game_mode:
        d = app.ui.active_art.layers_z[app.ui.active_art.active_layer]
    else:
        d = 0
    x, y, z = line_plane_intersection(0, 0, 1, d, start_x, start_y, start_z,
                                      end_x, end_y, end_z)
    if not x: return 0, 0, 0
    # DEBUG
    #print('ray start: %.4f, %.4f, %.4f\nray end: %.4f, %.4f, %.4f' % (start_x, start_y, start_z, end_x, end_y, end_z))
    colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]
    app.debug_line_renderable.set_lines([(start_x, start_y, start_z),
                                         (end_x, end_y, end_z),
                                         (x, y, z)],
                                        colors)
    return x, y, z

def _screen_to_world_NEW2(app, screen_x, screen_y):
    "2nd alternative implementation of screen_to_world"
    #worldPoint = inverse(projectionMatrix) * vec4(x * 2.0 / screenWidth - 1.0, (screenHeight - y) * 2.0 / screenHeight - 1.0, 0.0, 1.0)
    x = screen_x * 2 / app.window_width - 1
    y = (app.window_height - screen_y) * 2 / app.window_height - 1
    #inv_proj = np.matrix(app.camera.projection_matrix).getI()
    pjm = np.matrix(app.camera.projection_matrix)
    vm = np.matrix(app.camera.view_matrix)
    inv_proj = (pjm * vm).getI()
    #x, y, z = inv_proj.dot(np.array([x, y, 0, 1]))
    #x, y, z = inv_proj.dot([x, y, 0, 1])
    hi = inv_proj.dot([x, y, 0, 1]).getA()
    return hi[0][0] + app.camera.x, hi[0][1] + app.camera.y, hi[0][2]
    #return x, y, z

def _screen_to_world_OLD(app, screen_x, screen_y):
    "(existing Playscii 0.7.3 implementation)"
    # "normalized device coordinates"
    ndc_x = (2 * screen_x) / app.window_width - 1
    ndc_y = (-2 * screen_y) / app.window_height + 1
    # reverse camera projection
    pjm = np.matrix(app.camera.projection_matrix)
    vm = np.matrix(app.camera.view_matrix)
    vp_inverse = (pjm * vm).getI()
    if app.ui.active_art and not app.game_mode:
        z = app.ui.active_art.layers_z[app.ui.active_art.active_layer]
    else:
        z = 0
    point = vp_inverse.dot(np.array([ndc_x, ndc_y, z, 0]))
    point = point.getA()
    cz = app.camera.z - z
    # apply camera offsets
    x = point[0][0] * cz + app.camera.x
    y = point[0][1] * cz + app.camera.y
    # TODO: below doesn't properly account for distance between current
    # layer and camera - close but still inaccurate as cursor gets further
    # from world origin
    #y += self.app.camera.look_y.y
    #y += app.camera.y_tilt
    # DEBUG
    #print('%s, %s, %s' % (app.camera.x, app.camera.y, app.camera.z))
    #colors = [(1, 0, 0, 1), (0, 0, 1, 1), (0, 1, 0, 1), (1, 1, 0, 1)]
    #app.debug_line_renderable.set_lines(
    #    [(0, 0, 0), (x, y, z), (x, y, 0), (app.camera.x, app.camera.y, app.camera.z)],
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

def _screen_to_world_NEW3(app, screen_x, screen_y):
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
    """
    # leftover debug junk
    colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]
    app.debug_line_renderable.set_lines([(start_x, start_y, start_z),
                                         (end_x, end_y, end_z),
                                         (end_x, end_y, 0)],
                                        colors)
    """
    x, y, z = ray_plane_intersection(0, 0, plane_z, # plane loc
                                     0, 0, 1, # plane dir
                                     end_x, end_y, end_z, # ray loc
                                     dir_x, dir_y, dir_z) # ray dir
    return x, y, z

def _screen_to_world_NEW4(app, screen_x, screen_y):
    screen_x = (2 * screen_x) / app.window_width - 1
    screen_y = (-2 * screen_y) / app.window_height + 1
    ray_clip = np.array([screen_x, screen_y, -1, 1])
    ipjm = np.matrix(app.camera.projection_matrix, dtype=np.float32).getI()
    ivm = np.matrix(app.camera.view_matrix, dtype=np.float32).getI()
    ray_eye = ipjm.dot(ray_clip)
    ray_eye = ray_eye.getA().flatten()
    ray_eye[2] = -1
    ray_eye[3] = 0
    ray_wor = ivm.dot(ray_eye)
    ray_wor = ray_wor.getA().flatten()[:3]
    norm = np.linalg.norm(ray_wor)
    if norm != 0:
        ray_wor[0] /= norm
        ray_wor[1] /= norm
        ray_wor[2] /= norm
    #print(ray_wor)
    ray_eye += np.array([app.camera.x, app.camera.y, app.camera.z, 0])
    end_x = ray_eye[0] + ray_wor[0] * 100
    end_y = ray_eye[1] + ray_wor[1] * 100
    end_z = ray_eye[2] + ray_wor[2] * 100
    colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 0, 1)]
    app.debug_line_renderable.set_lines([(ray_eye[0], ray_eye[1], ray_eye[2]),
                                         (end_x, end_y, end_z)],
                                        colors)
    return 0, 0, 0

def screen_to_world(app, screen_x, screen_y):
    """
    Return 3D (float) world space coordinates for given 2D (int) screen space
    coordinates.
    """
    return _screen_to_world_NEW3(app, screen_x, screen_y)

def world_to_screen(app, world_x, world_y, world_z):
    """
    Return 2D screen pixel space coordinates for given 3D (float) world space
    coordinates.
    """
    pjm = np.matrix(app.camera.projection_matrix, dtype=np.float64)
    vm = np.matrix(app.camera.view_matrix, dtype=np.float64)
    # viewport tuple order should be same as glGetFloatv(GL_VIEWPORT)
    viewport = (0, 0, app.window_width, app.window_height)
    x, y, z = GLU.gluProject(world_x, world_y, world_z, vm, pjm, viewport)
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
