import ctypes


class VEC3(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
    ]

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        s = "["
        for field in self._fields_:
            s += str(getattr(self, field[0])) + ", "
        s +="]"
        return s


class VEC4(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("w", ctypes.c_float),
    ]

    def __init__(self, x, y, z, w=1):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    def __repr__(self):
        s = "["
        for field in self._fields_:
            s += str(getattr(self, field[0])) + ", "
        s +="]"
        return s


class VERTEX(ctypes.Structure):
    _fields_ = [
        ("vx", ctypes.c_float),
        ("vy", ctypes.c_float),
        ("vz", ctypes.c_float),
        ("px", ctypes.c_float),

        ("nx", ctypes.c_float),
        ("ny", ctypes.c_float),
        ("nz", ctypes.c_float),
        ("py", ctypes.c_float),
    ]

    def __repr__(self):
        s = "["
        for field in self._fields_:
            s += str(getattr(self, field[0])) + ", "
        s +="]"
        return s


class TRIANGLE(ctypes.Structure):
    _fields_ = [
        ("v0", ctypes.c_uint),
        ("v1", ctypes.c_uint),
        ("v2", ctypes.c_uint),
        ("pad", ctypes.c_uint),
    ]

    def __init__(self, v0, v1, v2):
        self.v0 = v0
        self.v1 = v1
        self.v2 = v2


class RAY(ctypes.Structure):
    _fields_ = [
        ("ox", ctypes.c_float),
        ("oy", ctypes.c_float),
        ("oz", ctypes.c_float),
        ("tmin", ctypes.c_float),

        ("dx", ctypes.c_float),
        ("dy", ctypes.c_float),
        ("dz", ctypes.c_float),
        ("tmax", ctypes.c_float),
    ]


class RAY_HIT(ctypes.Structure):
    _fields_ = [
        ("t", ctypes.c_float),
        ("tri_id", ctypes.c_int32),
        ("u", ctypes.c_float),
        ("v", ctypes.c_float),
    ]


class GPU_MESH(ctypes.Structure):
    _fields_ = [
        ("voxel_resolution", VEC4),
        ("aabb", (VEC4 * 2)),
        ("voxel_data", ctypes.c_uint64),
        ("voxel_list", ctypes.c_uint64),
        ("tri_buffer", ctypes.c_uint64),
        ("vert_buffer", ctypes.c_uint64),
        ("norm_buffer", ctypes.c_uint64),
        ("pad0", ctypes.c_float),
        ("pad1", ctypes.c_float),
    ]
