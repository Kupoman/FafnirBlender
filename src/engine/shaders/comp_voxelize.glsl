#version 440
const uint LIST_END = 0xFFFFFFFF;

layout(r32ui) uniform uimage3D voxels;
layout(rg32ui) uniform uimage2D link_list;
layout(r32ui, binding = 2) uniform uimage2D counter;

uniform usamplerBuffer tri_buffer;
uniform samplerBuffer vert_buffer;

uniform vec3 u_size;
uniform vec3 u_res;
uniform vec3 u_aabb[2];
uniform int u_count;

struct Triangle {
	int v0, v1, v2, pad;
};

void fetch_triangle(int i, inout Triangle triangle)
{
	triangle.v0 = int(texelFetch(tri_buffer, i * 3 + 0).x);
	triangle.v1 = int(texelFetch(tri_buffer, i * 3 + 1).x);
	triangle.v2 = int(texelFetch(tri_buffer, i * 3 + 2).x);
	triangle.pad = 0;
}

layout (local_size_x = 1, local_size_y = 1, local_size_z = 1) in;
void main()
{
	int work_id = int(gl_WorkGroupID.y * gl_NumWorkGroups.x + gl_WorkGroupID.x);
	if (work_id >= u_count)
		return;

	Triangle triangle;
	fetch_triangle(work_id, triangle);

	vec3 v0 = texelFetch(vert_buffer, triangle.v0).xyz;
	vec3 v1 = texelFetch(vert_buffer, triangle.v1).xyz;
	vec3 v2 = texelFetch(vert_buffer, triangle.v2).xyz;

	v0 = u_res * (v0 - u_aabb[0]) / u_size;
	v1 = u_res * (v1 - u_aabb[0]) / u_size;
	v2 = u_res * (v2 - u_aabb[0]) / u_size;

	ivec3 bb_min = ivec3(floor(min(min(v0, v1), v2)));
	ivec3 bb_max = ivec3(ceil(max(max(v0, v1), v2)));

	uint width = uint(imageSize(link_list).x);


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
