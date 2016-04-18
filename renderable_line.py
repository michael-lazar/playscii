import math, time, ctypes, platform
import numpy as np
from OpenGL import GL
from renderable import TileRenderable

class LineRenderable():
    
    "Renderable comprised of GL_LINES"
    
    vert_shader_source = 'lines_v.glsl'
    vert_shader_source_3d = 'lines_3d_v.glsl'
    frag_shader_source = 'lines_f.glsl'
    log_create_destroy = False
    line_width = 1
    # items in vert array: 2 for XY-only renderables, 3 for ones that include Z
    vert_items = 2
    # use game object's art_off_pct values
    use_art_offset = True
    
    def __init__(self, app, quad_size_ref, game_object=None):
        self.app = app
        # we may be attached to a game object
        self.game_object = game_object
        self.unique_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        self.quad_size_ref = quad_size_ref
        self.x, self.y, self.z = 0, 0, 0
        self.scale_x, self.scale_y = 1, 1
        # handle Z differently if verts are 2D vs 3D
        self.scale_z = 0 if self.vert_items == 2 else 1
        self.build_geo()
        self.width, self.height = self.get_size()
        self.reset_loc()
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        if self.vert_items == 3:
            self.vert_shader_source = self.vert_shader_source_3d
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        # uniforms
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.scale_uniform = self.shader.get_uniform_location('objectScale')
        self.quad_size_uniform = self.shader.get_uniform_location('quadSize')
        self.color_uniform = self.shader.get_uniform_location('objectColor')
        # vert buffers
        self.vert_buffer, self.elem_buffer = GL.glGenBuffers(2)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_array.nbytes,
                        self.vert_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_array.nbytes,
                        self.elem_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        self.vert_count = int(len(self.elem_array))
        self.pos_attrib = self.shader.get_attrib_location('vertPosition')
        GL.glEnableVertexAttribArray(self.pos_attrib)
        offset = ctypes.c_void_p(0)
        GL.glVertexAttribPointer(self.pos_attrib, self.vert_items,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        # vert colors
        self.color_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.color_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.color_array.nbytes,
                        self.color_array, GL.GL_STATIC_DRAW)
        self.color_attrib = self.shader.get_attrib_location('vertColor')
        GL.glEnableVertexAttribArray(self.color_attrib)
        GL.glVertexAttribPointer(self.color_attrib, 4,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
        if self.log_create_destroy:
            self.app.log('created: %s' % self)
    
    def __str__(self):
        "for debug purposes, return a unique name"
        return self.unique_name
    
    def build_geo(self):
        """
        create self.vert_array, self.elem_array, self.color_array
        """
        pass
    
    def reset_loc(self):
        pass
    
    def update(self):
        if self.game_object:
            self.update_transform_from_object(self.game_object)
    
    def reset_size(self):
        self.width, self.height = self.get_size()
    
    def update_transform_from_object(self, obj):
        TileRenderable.update_transform_from_object(self, obj)
    
    def rebind_buffers(self):
        # resend verts
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_array.nbytes,
                        self.vert_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_array.nbytes,
                        self.elem_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        self.vert_count = int(len(self.elem_array))
        # resend color
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.color_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.color_array.nbytes,
                        self.color_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    
    def get_projection_matrix(self):
        return np.eye(4, 4)
    
    def get_view_matrix(self):
        return np.eye(4, 4)
    
    def get_loc(self):
        return self.x, self.y, self.z
    
    def get_size(self):
        # overriden in subclasses that need specific width/height data
        return 1, 1
    
    def get_quad_size(self):
        return self.quad_size_ref.quad_width, self.quad_size_ref.quad_height
    
    def get_color(self):
        return (1, 1, 1, 1)
    
    def destroy(self):
        GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(3, [self.vert_buffer, self.elem_buffer, self.color_buffer])
        if self.log_create_destroy:
            self.app.log('destroyed: %s' % self)
    
    def render(self):
        GL.glUseProgram(self.shader.program)
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.get_projection_matrix())
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.get_view_matrix())
        GL.glUniform3f(self.position_uniform, *self.get_loc())
        GL.glUniform3f(self.scale_uniform, self.scale_x, self.scale_y, self.scale_z)
        GL.glUniform2f(self.quad_size_uniform, *self.get_quad_size())
        GL.glUniform4f(self.color_uniform, *self.get_color())
        GL.glBindVertexArray(self.vao)
        # bind elem array - see similar behavior in Cursor.render
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        if platform.system() != 'Darwin':
            GL.glLineWidth(self.line_width)
        GL.glDrawElements(GL.GL_LINES, self.vert_count,
                          GL.GL_UNSIGNED_INT, None)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)


# common data/code used by various boxes
BOX_VERTS = [(0, 0), (1, 0), (1, -1), (0, -1)]

def get_box_arrays(vert_list=None, color=(1, 1, 1, 1)):
    verts = np.array(vert_list or BOX_VERTS, dtype=np.float32)
    elems = np.array([0, 1, 1, 2, 2, 3, 3, 0], dtype=np.uint32)
    colors = np.array([color * 4], dtype=np.float32)
    return verts, elems, colors


class UIRenderableX(LineRenderable):
    
    "Red X used to denote transparent color in various places"
    color = (1, 0, 0, 1)
    line_width = 2
    
    def build_geo(self):
        self.vert_array = np.array([(0, 0), (1, 1), (1, 0), (0, 1)], dtype=np.float32)
        self.elem_array = np.array([0, 1, 2, 3], dtype=np.uint32)
        self.color_array = np.array([self.color * 4], dtype=np.float32)


class SwatchSelectionBoxRenderable(LineRenderable):
    
    "used for UI selection boxes etc"
    
    color = (0.5, 0.5, 0.5, 1)
    line_width = 2
    
    def __init__(self, app, quad_size_ref):
        LineRenderable.__init__(self, app, quad_size_ref)
        # track tile X and Y for cursor movement
        self.tile_x, self.tile_y = 0,0
    
    def get_color(self):
        return self.color
    
    def build_geo(self):
        self.vert_array, self.elem_array, self.color_array = get_box_arrays(None, self.color)


class WorldLineRenderable(LineRenderable):
    "any LineRenderable that draws in world, ie in 3D perspective"
    def get_projection_matrix(self):
        return self.app.camera.projection_matrix
    
    def get_view_matrix(self):
        return self.app.camera.view_matrix


class OriginIndicatorRenderable(WorldLineRenderable):
    
    "classic 3-axis thingy showing location/rotation/scale"
    
    red   = (1.0, 0.1, 0.1, 1.0)
    green = (0.1, 1.0, 0.1, 1.0)
    blue  = (0.1, 0.1, 1.0, 1.0)
    origin = (0, 0, 0)
    x_axis = (1, 0, 0)
    y_axis = (0, 1, 0)
    z_axis = (0, 0, 1)
    vert_items = 3 
    line_width = 3
    use_art_offset = False
    
    def __init__(self, app, game_object):
        LineRenderable.__init__(self, app, None, game_object)
    
    def get_quad_size(self):
        return 1, 1
    
    def get_size(self):
        return self.game_object.scale_x, self.game_object.scale_y
    
    def update_transform_from_object(self, obj):
        self.x, self.y, self.z = obj.x, obj.y, obj.z
        self.scale_x, self.scale_y = obj.scale_x, obj.scale_y
        if obj.flip_x:
            self.scale_x *= -1
        self.scale_z = obj.scale_z
    
    def build_geo(self):
        self.vert_array = np.array([self.origin, self.x_axis,
                                    self.origin, self.y_axis,
                                    self.origin, self.z_axis],
                                    dtype=np.float32)
        self.elem_array = np.array([0, 1, 2, 3, 4, 5], dtype=np.uint32)
        self.color_array = np.array([self.red, self.red, self.green, self.green,
                                     self.blue, self.blue], dtype=np.float32)

class BoundsIndicatorRenderable(WorldLineRenderable):
    color = (1, 1, 1, 0.5)
    
    def __init__(self, app, game_object):
        self.art = game_object.renderable.art
        LineRenderable.__init__(self, app, None, game_object)
    
    def set_art(self, new_art):
        self.art = new_art
        self.reset_size()
    
    def get_size(self):
        art = self.game_object.art
        w = (art.width * art.quad_width) * self.game_object.scale_x
        h = (art.height * art.quad_height) * self.game_object.scale_y
        return w, h
    
    def get_color(self):
        # pulse if selected
        if self.game_object in self.app.gw.selected_objects:
            color = 0.75 + (math.sin(self.app.get_elapsed_time() / 100) / 2)
            return (color, color, color, 1)
        else:
            return (1, 1, 1, 1)
    
    def get_quad_size(self):
        if not self.game_object:
            return 1, 1
        return self.art.width * self.art.quad_width, self.art.height * self.art.quad_height
    
    def build_geo(self):
        self.vert_array, self.elem_array, self.color_array = get_box_arrays(None, self.color)


class CollisionRenderable(WorldLineRenderable):
    
    # green = dynamic, blue = static
    dynamic_color = (0, 1, 0, 1)
    static_color = (0, 0, 1, 1)
    
    def __init__(self, shape):
        self.color = self.dynamic_color if shape.game_object.is_dynamic() else self.static_color
        self.shape = shape
        WorldLineRenderable.__init__(self, shape.game_object.app, None,
                                     shape.game_object)
    
    def update(self):
        self.update_transform_from_object(self.shape)
    
    def update_transform_from_object(self, obj):
        self.x = obj.x
        self.y = obj.y


def get_circle_points(radius, steps=24):
    angle = 0
    points = [(radius, 0)]
    for i in range(steps):
        angle += math.radians(360 / steps)
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        points.append((x, y))
    return points


class CircleCollisionRenderable(CollisionRenderable):
    
    line_width = 2
    segments = 24
    
    def get_quad_size(self):
        return self.shape.radius, self.shape.radius
    
    def get_size(self):
        w = h = self.shape.radius * 2
        w *= self.game_object.scale_x
        h *= self.game_object.scale_y
        return w, h
    
    def build_geo(self):
        verts, elements, colors = [], [], []
        angle = 0
        last_x, last_y = 1, 0
        i = 0
        while i < self.segments * 4:
            angle += math.radians(360 / self.segments)
            verts.append((last_x, last_y))
            x = math.cos(angle)
            y = math.sin(angle)
            verts.append((x, y))
            last_x, last_y = x, y
            elements.append((i, i+1))
            i += 2
            colors.append([self.color * 2])
        self.vert_array = np.array(verts, dtype=np.float32)
        self.elem_array = np.array(elements, dtype=np.uint32)
        self.color_array = np.array(colors, dtype=np.float32)


class BoxCollisionRenderable(CollisionRenderable):
    
    line_width = 2
    
    def get_quad_size(self):
        return self.shape.halfwidth * 2, self.shape.halfheight * 2
    
    def get_size(self):
        w, h = self.shape.halfwidth * 2, self.shape.halfheight * 2
        w *= self.game_object.scale_x
        h *= self.game_object.scale_y
        return w, h
    
    def build_geo(self):
        verts = [(-0.5, 0.5), (0.5, 0.5), (0.5, -0.5), (-0.5, -0.5)]
        self.vert_array, self.elem_array, self.color_array = get_box_arrays(verts, self.color)


class TileBoxCollisionRenderable(BoxCollisionRenderable):
    "box for each tile in a CST_TILE object"
    line_width = 1
    def get_loc(self):
        # draw at Z level of collision layer
        art = self.game_object.art
        col_index = art.layer_names.index(self.game_object.col_layer_name)
        return self.x, self.y, self.z + art.layers_z[col_index]
