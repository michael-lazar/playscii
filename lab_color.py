# L*a*b color space conversion
# from EDSCII

import math

def rgb_to_xyz(r, g, b):
    r /= 255.0
    g /= 255.0
    b /= 255.0
    if r > 0.04045:
        r = ((r + 0.055) / 1.055)**2.4
    else:
        r /= 12.92
    if g > 0.04045:
        g = ((g + 0.055) / 1.055)**2.4
    else:
        g /= 12.92
    if b > 0.04045:
        b = ((b + 0.055) / 1.055)**2.4
    else:
        b /= 12.92
    r *= 100
    g *= 100
    b *= 100
    # observer: 2deg, illuminant: D65
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    return x, y, z

def xyz_to_lab(x, y, z):
    # observer: 2deg, illuminant: D65
    x /= 95.047
    y /= 100.0
    z /= 108.883
    if x > 0.008856:
        x = x**(1.0/3)
    else:
        x = (7.787 * x) + (16.0 / 116)
    if y > 0.008856:
        y = y**(1.0/3)
    else:
        y = (7.787 * y) + (16.0 / 116)
    if z > 0.008856:
        z = z**(1.0/3)
    else:
        z = (7.787 * z) + (16.0 / 116)
    l = (116 * y) - 16
    a = 500 * (x - y)
    b = 200 * (y - z)
    return l, a, b

def rgb_to_lab(r, g, b):
    x, y, z = rgb_to_xyz(r, g, b)
    return xyz_to_lab(x, y, z)

def lab_color_diff(l1, a1, b1, l2, a2, b2):
    "quick n' dirty CIE 1976 color delta"
    dl = (l1 - l2)**2
    da = (a1 - a2)**2
    db = (b1 - b2)**2
    return math.sqrt(dl + da + db)
