import numpy as np
from OpenGL import GL

class Texture:
    
    # TODO: move texture data init to a set method to make hot reload trivial(?)
    
    mag_filter = GL.GL_NEAREST
    min_filter = GL.GL_NEAREST
    #min_filter = GL.GL_NEAREST_MIPMAP_NEAREST
    packing = GL.GL_UNPACK_ALIGNMENT
    
    def __init__(self, string_data, width, height):
        self.width, self.height = width, height
        img_data = np.fromstring(string_data, dtype=np.uint8)
        self.gltex = GL.glGenTextures(1)
        GL.glPixelStorei(self.packing, 1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.gltex)
        self.set_filter(self.mag_filter, self.min_filter, False)
        self.set_wrap(False, False)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img_data)
        if bool(GL.glGenerateMipmap):
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
    
    def set_filter(self, new_mag_filter, new_min_filter, bind_first=True):
        if bind_first:
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.gltex)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, new_mag_filter)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, new_min_filter)
    
    def set_wrap(self, new_wrap, bind_first=True):
        if bind_first:
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.gltex)
        wrap = GL.GL_REPEAT if new_wrap else GL.GL_CLAMP_TO_EDGE
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, wrap)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, wrap)
    
    def destroy(self):
        GL.glDeleteTextures([self.gltex])
