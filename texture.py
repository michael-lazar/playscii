import numpy
from OpenGL import GL
from PIL import Image

class Texture:
    
    # TODO: move texture data init to a set method to make hot reload trivial(?)
    
    mag_filter = GL.GL_NEAREST
    min_filter = GL.GL_NEAREST_MIPMAP_NEAREST
    wrap = GL.GL_CLAMP_TO_EDGE
    packing = GL.GL_UNPACK_ALIGNMENT
    
    def __init__(self, string_data, width, height):
        self.width, self.height = width, height
        img_data = numpy.fromstring(string_data, numpy.uint8)
        self.gltex = GL.glGenTextures(1)
        GL.glPixelStorei(self.packing, 1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.gltex)
        self.set_filter(self.mag_filter, self.min_filter, False)
        self.set_wrap(self.wrap, False)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img_data)
        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
    
    def set_filter(self, new_mag_filter, new_min_filter, bind_first=True):
        if bind_first:
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.gltex)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, new_mag_filter)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, new_min_filter)
    
    def set_wrap(self, new_wrap, bind_first=True):
        if bind_first:
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.gltex)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, new_wrap)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, new_wrap)


class TextureFromFile(Texture):
    
    def __init__(self, filename, transparent_color=(0, 0, 0)):
        img = Image.open(filename)
        img = img.convert('RGBA')
        width, height = img.size
        # any pixel that is "transparent color" will be made fully transparent
        # any pixel that isn't will be opaque + tinted FG color
        for y in range(height):
            for x in range(width):
                color = img.getpixel((x, y))
                if color[:3] == transparent_color[:3]:
                    # TODO: does keeping non-alpha color improve sampling?
                    img.putpixel((x, y), (color[0], color[1], color[2], 0))
        Texture.__init__(self, img.tostring(), width, height)
