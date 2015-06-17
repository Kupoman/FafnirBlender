bl_info = {
	"name": "Fafnir",
	"author": "Daniel Stokes",
	"blender": (2, 74, 0),
	"location": "Info header, render engine menu",
	"description": "Fafnir integration",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"support": 'TESTING',
	"category": "Render"}


import bpy

from .addon_engine import FafnirEngine


def register():
	panels = [getattr(bpy.types, t) for t in dir(bpy.types) if 'PT' in t]
	for panel in panels:
		if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_GAME' in panel.COMPAT_ENGINES:
			panel.COMPAT_ENGINES.add('FAFNIR')
	bpy.utils.register_module(__name__)


def unregister():
	panels = [getattr(bpy.types, t) for t in dir(bpy.types) if 'PT' in t]
	for panel in panels:
		if hasattr(panel, 'COMPAT_ENGINES') and 'RTE_FRAMEWORK' in panel.COMPAT_ENGINES:
			panel.COMPAT_ENGINES.remove('FAFNIR')
	bpy.utils.unregister_module(__name__)
