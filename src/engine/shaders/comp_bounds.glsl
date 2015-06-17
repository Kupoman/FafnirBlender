#version 440

layout(r32ui, binding = 0) uniform uimage3D voxels;

struct Vertex {
	vec4 position;
};

layout(std430, binding=1) buffer VertBuffer {
	Vertex vertex_buffer[];
};

layout (local_size_x = 1, local_size_y = 1, local_size_z = 1) in;
void main()
{
	imageStore(voxels, ivec3(gl_WorkGroupID.xyz), uvec4(LIST_END));
}