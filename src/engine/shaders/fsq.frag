#version 440
#extension GL_ARB_shader_storage_buffer_object: enable

#define VOXEL

const float epsilon = 0.00001;
const uint LIST_END = 0xFFFFFFFF;

layout(binding=0) uniform usampler3D voxels;
// layout(r32ui, binding = 0) uniform uimage3D voxels;
layout(binding=1) uniform usampler2D link_list;
uniform int num_triangles;

uniform float u_size;
uniform float u_res;
uniform vec3 u_aabb[2];

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

in vec3 in_vertex;
in vec3 in_ray_o;
in vec3 in_ray_d;
in vec3 in_ray_inv;

out vec3 out_color;

int texture_width = textureSize(link_list, 0).x;

bool trace_list(uint ptr, vec3 ray_o, vec3 ray_d, float closest_t)
{
	Vertex v0, v1, v2;
	vec3 v0p, v1p, v2p;
	Triangle triangle;
	vec3 e0, e1, T, P, Q;
	float det=1.0, inv_det, t, u=1.0, v=1.0;

	float closest_u, closest_v;
	uint closest_tri = -1;

#ifdef VOXEL
	while (ptr != LIST_END) {
		uvec2 link = texelFetch(link_list, ivec2(ptr % texture_width, ptr / texture_width), 0).rg;
		triangle = tri_buffer[link.x];
		ptr = link.y;
#else
	uint i = 0;
	for (; i < num_triangles; ++i) {
		triangle = tri_buffer[i];
#endif

		v0 = vertex_buffer[triangle.v0 + triangle.pad];
		v1 = vertex_buffer[triangle.v1 + triangle.pad];
		v2 = vertex_buffer[triangle.v2 + triangle.pad];
		v0p = v0.position.xyz;
		v1p = v1.position.xyz;
		v2p = v2.position.xyz;

		e0 = v1p - v0p;
		e1 = v2p - v0p;

		P = cross(ray_d, e1);
		det = dot(e0, P);

		if (det < epsilon) continue;

		T = ray_o - v0p;

		u = dot(T, P);
		if (u < 0.0 || u > det) continue;

		Q = cross(T, e0);

		v = dot(ray_d, Q);
		if (v < 0.0 || u + v > det) continue;


		inv_det = 1.0 / det;

		t = dot(e1, Q) * inv_det;

		if (t < closest_t) {
			closest_t = t;
			closest_u = u * inv_det;
			closest_v = v * inv_det;
#ifdef VOXEL
			closest_tri = link.x;
#else
			closest_tri = i;
#endif
		}
	}
	if (closest_tri != -1) {
		u = closest_u;
		v = closest_v;

		triangle = tri_buffer[closest_tri];

		vec3 pos = vertex_buffer[triangle.v0 + triangle.pad].position.xyz * (1-u-v);
		pos += vertex_buffer[triangle.v1 + triangle.pad].position.xyz * u;
		pos += vertex_buffer[triangle.v2 + triangle.pad].position.xyz * v;

		vec3 norm = vertex_buffer[triangle.v0 + triangle.pad].normal.xyz * (1-u-v);
		norm += vertex_buffer[triangle.v1 + triangle.pad].normal.xyz * u;
		norm += vertex_buffer[triangle.v2 + triangle.pad].normal.xyz * v;

		vec3 L = normalize(vec3(3.0, -4.0, 6.0) - pos);
		vec3 N = normalize(norm);

		out_color = vec3(dot(N, L) * 0.8);
		return true;
	}

	out_color = vec3(0.2, 0.2, 0.2);
	return false;
}

void main()
{
#ifdef VOXEL
	out_color = vec3(0.2);
	vec3 ray_o = in_ray_o;
	vec3 ray_d = normalize(in_ray_d);
	vec3 ray_inv = vec3(1.0) / ray_d;

	// Make sure we are in the voxel region
	vec3 ray_sign = step(0.0, -ray_inv);
	vec3 bounds = u_aabb[1] * ray_sign + u_aabb[0] * (ivec3(1) - ray_sign);
	vec3 t_vmin = (bounds - ray_o) * ray_inv;
	bounds = u_aabb[0] * ray_sign + u_aabb[1] * (ivec3(1) - ray_sign);
	vec3 t_vmax = (bounds - ray_o) * ray_inv;

	if (any(greaterThan(t_vmin.xyxz, t_vmax.yxzx)))
		discard;

	float tmin = max(max(t_vmin.x, t_vmin.y), t_vmin.z);
	float tmax = min(min(t_vmax.x, t_vmax.y), t_vmax.z);

	if (tmax <= tmin)
		discard;

	ray_o += ray_d * (tmin + epsilon);

	vec3 cell_size = vec3(u_size/u_res);
	ivec3 cell_coord = ivec3(floor((ray_o - u_aabb[0]) / cell_size));

	// Initialize DDA traversal variables
	vec3 cell_min = cell_coord * cell_size + u_aabb[0];
	vec3 cell_max = (cell_coord + vec3(1)) * cell_size + u_aabb[0];
	bounds = cell_min * ray_sign + cell_max * (ivec3(1) - ray_sign);
	vec3 dda_tmax = (bounds - ray_o) * ray_inv;
	ivec3 coord_step = ivec3(sign(ray_d));
	vec3 dda_step = cell_size * coord_step * ray_inv;

	// Traverse voxel grid
	while (!(any(lessThan(cell_coord, ivec3(0)))) && !(any(greaterThan(cell_coord, ivec3(u_res-1))))) {
		uint ptr = texelFetch(voxels, cell_coord, 0).r;
		float t = min(min(dda_tmax.x, dda_tmax.y), dda_tmax.z);
		if (trace_list(ptr, ray_o, ray_d, t))
			return;

		ivec3 mask = ivec3(step(-t, -dda_tmax));
		cell_coord += mask * coord_step;
		dda_tmax += mask * dda_step;
	}

	discard;
#else
	trace_list(0);
#endif
}