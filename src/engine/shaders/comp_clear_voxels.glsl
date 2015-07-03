#version 440
const uint LIST_END = 0xFFFFFFFF;

layout(r32ui) uniform uimage3D voxels;

layout (local_size_x = 1, local_size_y = 1, local_size_z = 1) in;
void main()
{
	imageStore(voxels, ivec3(gl_WorkGroupID.xyz), uvec4(LIST_END));
}