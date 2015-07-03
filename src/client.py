import base64
import ctypes
import json
import math
import random
import socket
import struct
import time

from socket_api import *
from engine.engine import Engine, VEC3, Mesh

from OpenGL.GLUT import *
from OpenGL.GL import *
from OpenGL.WGL import *

g_width = 1506
g_height = 871
g_pbo = 0
g_fbo = 0
g_render_target = 0
g_depth_target = 0
g_vmat = []
g_pmat = []
g_ready = False


img_data = (ctypes.c_ubyte * (g_width*g_height*3))()


g_socket = socket.socket()
g_time = time.perf_counter()


g_engine = None


USE_SOCKET = True


def update_img(width, height):
    global g_width, g_height, img_data

    g_width = 2 ** math.ceil(math.log2(width))
    g_height = 2 ** math.ceil(math.log2(height))
    img_data = bytearray((ctypes.c_ubyte * (g_width*g_height*3))())
    glBindTexture(GL_TEXTURE_2D, g_render_target)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, g_width, g_height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glBindRenderbuffer(GL_RENDERBUFFER, g_depth_target)
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT32F, g_width, g_height)
    glViewport(0, 0, g_width, g_height)


def display():
    global g_time

    mrays = 0
    start = time.perf_counter()
    if g_vmat and g_pmat:
        g_engine.draw(g_vmat, g_pmat)

    glBindBuffer(GL_PIXEL_PACK_BUFFER, g_pbo)
    if USE_SOCKET:
        glReadPixels(0, 0, g_width, g_height, GL_RGB, GL_UNSIGNED_BYTE, img_data)
    glutSwapBuffers()

    end = time.perf_counter()
    mrays = g_width * g_height / 1000000 / (end - start)

    handle_socket()

    new_time = time.perf_counter()
    glutSetWindowTitle("Fafnir %0.2f ms" % ((new_time - g_time) * 1000))
    # glutSetWindowTitle("Fafnir %0.2f mrays/s" % (mrays))
    g_time = new_time


def handle_socket():
    global g_socket, g_width, g_height, img_data, g_vmat, g_pmat, g_ready
    if not USE_SOCKET:
        return

    try:
        while True:
            try:
                g_socket.setblocking(False)
                message = g_socket.recv(1)
                if message:
                    g_socket.setblocking(True)
                    method_id, data_id = decode_cmd_message(message)
                    size = decode_size_message(g_socket.recv(4))
                    # print("Received", method_id.name, data_id.name, size)

                    data = b""
                    remaining = size
                    start = time.perf_counter()
                    while remaining > 0:
                        chunk = g_socket.recv(min(2**23, remaining))
                        remaining -= len(chunk)
                        data += chunk
                    data = json.loads(data.decode())
                    # print("Time to download data: %.2fs" % (time.perf_counter() - start))
                    if data_id == DataIDs.projection:
                        glMatrixMode(GL_PROJECTION)
                        glLoadMatrixf(data["data"])
                        g_pmat = data["data"]
                        g_engine._scene_dirty = True
                    elif data_id == DataIDs.view:
                        glMatrixMode(GL_MODELVIEW)
                        glLoadMatrixf(data["data"])
                        g_vmat = data["data"]
                    elif data_id == DataIDs.viewport:
                        update_img(data["width"], data["height"])
                        g_ready = True
                        g_engine._scene_dirty = True
                    elif data_id == DataIDs.gltf:
                        start = time.perf_counter()
                        handle_gltf(method_id, data)
                        print("Convert time: %.2f" % (time.perf_counter() - start))
            except BlockingIOError:
                break

        # Return output
        if g_ready:
            g_socket.setblocking(True)
            data_size = len(img_data)
            # print("Sending data of size", data_size)
            try:
                g_socket.send(struct.pack("HH", g_width, g_height))

                start_time = time.perf_counter()
                sent_count = 0

                while sent_count < data_size:
                    sent_count += g_socket.send(img_data[sent_count:])
            except socket.timeout:
                print("Failed to send result data")

            etime = time.perf_counter() - start_time
            tx = 0 if etime == 0 else sent_count*8/1024/1024/etime
            # print("Sent %d bytes in %.2f ms (%.2f Mbps)" % (sent_count, etime*1000, tx))
    except ConnectionResetError:
        print("Connection reset")
        close()


def close():
    print("Exiting client")
    if USE_SOCKET:
        g_socket.close()
    sys.exit()


def main():
    global img_data, g_socket, g_fbo, g_render_target, g_pbo, g_depth_target, g_engine, g_ready

    # Init result image buffer
    for i in range(len(img_data), ):
        img_data[i] = 128
    img_data = bytearray(img_data)

    # Init socket connection
    if USE_SOCKET:
        g_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        g_socket.connect(("127.0.0.1", 4242))
    else:
        g_ready = True

    # Init Glut
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(320, 240)
    glutInitWindowPosition(2100, 100)
    glutCreateWindow(b"Fafnir Client")
    if USE_SOCKET:
        glutHideWindow()
    glutIdleFunc(display)

    # Setup framebuffer
    g_fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, g_fbo)
    g_render_target = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, g_render_target)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, g_render_target, 0)
    g_depth_target = glGenRenderbuffers(1)
    glBindRenderbuffer(GL_RENDERBUFFER, g_depth_target)
    update_img(g_width, g_height)
    if not USE_SOCKET:
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    g_engine = Engine()

    glutMainLoop()


def handle_gltf(method_id, data):
    meshes = data["meshes"]

    for name, mesh in meshes.items():
        for i, primitive in enumerate(mesh["primitives"]):
            accessor = data["accessors"][primitive["indices"]]
            element_count = accessor["count"]

            attributes = primitive["attributes"]
            accessor = data["accessors"][attributes["POSITION"]]
            vert_count = accessor["count"]

            # Positions
            attributes = primitive["attributes"]
            accessor = data["accessors"][attributes["POSITION"]]
            bufview = data["bufferViews"][accessor["bufferView"]]
            buf = data["buffers"][bufview["buffer"]]
            bufdata = base64.b64decode(buf["uri"].split(",")[1])
            offset = bufview["byteOffset"]+accessor["byteOffset"]
            stride = accessor["byteStride"]
            positions = (VEC3 * vert_count)()
            for j in range(vert_count):
                positions[j].x = struct.unpack("f", bufdata[offset + j * stride + 0:offset + j * stride + 4])[0]
                positions[j].y = struct.unpack("f", bufdata[offset + j * stride + 4:offset + j * stride + 8])[0]
                positions[j].z = struct.unpack("f", bufdata[offset + j * stride + 8:offset + j * stride + 12])[0]

            # Normals
            attributes = primitive["attributes"]
            accessor = data["accessors"][attributes["NORMAL"]]
            bufview = data["bufferViews"][accessor["bufferView"]]
            buf = data["buffers"][bufview["buffer"]]
            bufdata = base64.b64decode(buf["uri"].split(",")[1])
            offset = bufview["byteOffset"]+accessor["byteOffset"]
            stride = accessor["byteStride"]
            normals = (VEC3 * vert_count)()
            for j in range(vert_count):
                normals[j].x = struct.unpack("f", bufdata[offset + j * stride + 0:offset + j * stride + 4])[0]
                normals[j].y = struct.unpack("f", bufdata[offset + j * stride + 4:offset + j * stride + 8])[0]
                normals[j].z = struct.unpack("f", bufdata[offset + j * stride + 8:offset + j * stride + 12])[0]

            # Indices
            accessor = data["accessors"][primitive["indices"]]
            bufview = data["bufferViews"][accessor["bufferView"]]
            buf = data["buffers"][bufview["buffer"]]
            bufdata = base64.b64decode(buf["uri"].split(",")[1])
            offset = bufview["byteOffset"]+accessor["byteOffset"]
            indices = (ctypes.c_ushort * element_count).from_buffer_copy(bufdata, offset)

            mesh_name = name + "_prim" + str(i)
            mesh_data = Mesh(vert_count, element_count, positions, normals, indices)
            g_engine.add_or_update_mesh(mesh_name, mesh_data)

    for name, node in data["nodes"]:
        print(name)


def update_object(data_bytes):
    print("Object update: " + data_bytes.decode())


def update_material(data_bytes):
    print("Material update: " + data_bytes.decode())


main()