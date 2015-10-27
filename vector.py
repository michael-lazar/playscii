import math

class Vec3:
    
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
    
    def __str__(self):
        return 'Vec3 %.4f, %.4f, %.4f' % (self.x, self.y, self.z)
    
    def __sub__(self, b):
        return Vec3(self.x - b.x, self.y - b.y, self.z - b.z)
    
    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)
    
    def normalize(self):
        "returns a unit length version of this vector"
        n = Vec3()
        l = self.length()
        if l != 0:
            ilength = 1.0 / l
            n.x = self.x * ilength
            n.y = self.y * ilength
            n.z = self.z * ilength
        return n
    
    def cross(self, b):
        x = self.y * b.z - self.z * b.y
        y = self.z * b.x - self.x * b.z
        z = self.x * b.y - self.y * b.x
        return Vec3(x, y, z)
    
    def dot(self, b):
        return self.x * b.x + self.y * b.y + self.z * b.z
    
    def inverse(self):
        return Vec3(-self.x, -self.y, -self.z)
    
    def copy(self):
        return Vec3(self.x, self.y, self.z)
