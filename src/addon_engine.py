import os
import sys

import bpy

from .BlenderRealtimeEngineAddon.engine import RealTimeEngine


path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(path)


class FafnirEngine(bpy.types.RenderEngine, RealTimeEngine):
	bl_idname = 'FAFNIR'
	bl_label = "Fafnir"

	def __init__(self):
		watch_list_names = [
			"meshes",
		]

		client_dir = os.path.dirname(os.path.realpath(__file__))
		program = ("python", client_dir + "/client.py")

		RealTimeEngine.__init__(self, program, watch_list_names)