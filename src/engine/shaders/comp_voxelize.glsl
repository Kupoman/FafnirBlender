#version 440
// #extension GL_ARB_shader_storage_buffer_object: enable
const uint LIST_END = 0xFFFFFFFF;

layout(r32ui, binding = 0) uniform uimage3D voxels;
layout(rg32ui, binding = 1) uniform uimage2D link_list;
layout(r32ui, binding = 2) uniform uimage2D counter;

uniform float u_size;
uniform float u_res;
uniform vec3 u_aabb[2];
uniform int u_count;

struct Triangle {
	uint v0, v1, v2, pad;
};

layout(std430, binding=0) buffer TriBuffer {
	Triangle tri_buffer[];
};

struct Vertex {
	vec4 position;
	vec4 normal;
};

layout(std430, binding=1) buffer VertBuffer {
	Vertex vertex_buffer[];
};



layout (local_size_x = 1, local_size_y = 1, local_size_z = 1) in;
void main()
{
	uint work_id = gl_WorkGroupID.y * gl_NumWorkGroups.x + gl_WorkGroupID.x;
	if (work_id >= u_count)
		return;

	Triangle tri = tri_buffer[work_id];

	vec3 v0 = vertex_buffer[tri.v0+tri.pad].position.xyz;
	vec3 v1 = vertex_buffer[tri.v1+tri.pad].position.xyz;
	vec3 v2 = vertex_buffer[tri.v2+tri.pad].position.xyz;

	v0 = u_res * (v0 - u_aabb[0]) / u_size;
	v1 = u_res * (v1 - u_aabb[0]) / u_size;
	v2 = u_res * (v2 - u_aabb[0]) / u_size;
	// v0 = ((v0 / (u_size * 0.5)) * vec3(0.5) + vec3(0.5))*u_res;
	// v1 = ((v1 / (u_size * 0.5)) * vec3(0.5) + vec3(0.5))*u_res;
	// v2 = ((v2 / (u_size * 0.5)) * vec3(0.5) + vec3(0.5))*u_res;

	ivec3 bb_min = ivec3(floor(min(min(v0, v1), v2)));
	ivec3 bb_max = ivec3(ceil(max(max(v0, v1), v2)));

	int width = imageSize(link_list).x;

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