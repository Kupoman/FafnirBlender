#version 440
#extension GL_ARB_bindless_texture: enable
const uint LIST_END = 0xFFFFFFFF;

layout(r32ui) uniform uimage3D voxels;
layout(rg32ui) uniform uimage2D link_list;
layout(r32ui, binding = 2) uniform uimage2D counter;

struct MeshData{
	vec4 voxel_resolution;
	vec4 aabb[2];
	layout(r32ui) uimage3D voxel_data;
	layout(rg32ui) uimage2D voxel_list;
	usamplerBuffer tri_buffer;
	samplerBuffer vert_buffer;
	samplerBuffer norm_buffer;
	float pad[2];
};

layout(std430, binding=0) buffer MeshBuffer {
	MeshData mesh_buffer[];
};
uniform int num_meshes;

uniform vec3 u_size;
uniform vec3 u_res;
uniform vec3 u_aabb[2];

layout (local_size_x = 1, local_size_y = 1, local_size_z = 1) in;
void main()
{
	int work_id = int(gl_WorkGroupID.y * gl_NumWorkGroups.x + gl_WorkGroupID.x);
	if (work_id >= num_meshes)
		return;

	int width = imageSize(link_list).x;

	MeshData mesh = mesh_buffer[work_id];
	ivec3 bb_min = ivec3(floor(u_res * (mesh.aabb[0].xyz - u_aabb[0]) / u_size));
	ivec3 bb_max = ivec3(ceil(u_res * (mesh.aabb[1].xyz - u_aabb[0]) / u_size));

	for (int z = bb_min.z; z < bb_max.z; ++z) {
		for (int y = bb_min.y; y < bb_max.y; ++y) {
			for (int x = bb_min.x; x < bb_max.x; ++x) {
				uint end = imageAtomicAdd(counter, ivec2(0, 0), 1) + 1;
				uint old_ptr = imageAtomicExchange(voxels, ivec3(x, y, z), end).r;
				ivec2 end_idx = ivec2(end%width, end/width);
				imageStore(link_list, end_idx, uvec4(work_id, old_ptr, 0, 0));
			}
		}
	}
}
