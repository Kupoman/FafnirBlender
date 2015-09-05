#version 440
#extension GL_ARB_bindless_texture: enable

#define VOXEL

const float epsilon = 0.00001;
const uint LIST_END = 0xFFFFFFFF;

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

// Global state
usamplerBuffer tri_buffer;
samplerBuffer vert_buffer;
samplerBuffer norm_buffer;
int num_triangles;

layout(std430, binding=0) buffer MeshBuffer {
	MeshData mesh_buffer[];
};
uniform int num_meshes;

struct Triangle {
	int v0, v1, v2, pad;
};

uniform vec3 scene_aabb[2];
uniform vec3 scene_resolution;
layout(r32ui) uniform uimage3D scene_voxels;
layout(rg32ui) uniform uimage2D scene_list;

in vec3 in_vertex;
in vec3 in_ray_o;
in vec3 in_ray_d;
in vec3 in_ray_inv;

out vec3 out_color;

void fetch_triangle(int i, inout Triangle triangle)
{
	triangle.v0 = int(texelFetch(tri_buffer, i * 3 + 0).x);
	triangle.v1 = int(texelFetch(tri_buffer, i * 3 + 1).x);
	triangle.v2 = int(texelFetch(tri_buffer, i * 3 + 2).x);
	triangle.pad = 0;
}

bool trace_list(uint ptr, layout(rg32ui) uimage2D link_list, int list_width,
	vec3 ray_o, vec3 ray_d, float closest_t, out int index, out vec3 hit)
{
	vec3 v0p, v1p, v2p;
	Triangle triangle;
	vec3 e0, e1, T, P, Q;
	float det=1.0, inv_det, t, u=1.0, v=1.0;

	float closest_u, closest_v;
	int closest_tri = -1;

#ifdef VOXEL
	while (ptr != LIST_END) {
		uvec2 link = imageLoad(link_list, ivec2(ptr % list_width, ptr / list_width)).rg;
		fetch_triangle(int(link.x), triangle);
		ptr = link.y;
#else
	int i = 0;
	for (; i < num_triangles; ++i) {
		fetch_triangle(i, triangle);
#endif

		v0p = texelFetch(vert_buffer, triangle.v0).xyz;
		v1p = texelFetch(vert_buffer, triangle.v1).xyz;
		v2p = texelFetch(vert_buffer, triangle.v2).xyz;

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

		if (t < 0) continue;

		if (t < closest_t) {
			closest_t = t;
			closest_u = u * inv_det;
			closest_v = v * inv_det;
#ifdef VOXEL
			closest_tri = int(link.x);
#else
			closest_tri = i;
#endif
		}
	}

	if (closest_tri != -1) {
		index = closest_tri;
		hit = vec3(closest_t, closest_u, closest_v);
		return true;
	}

	index = -1;
	hit = vec3(0.0);
	return false;
}

void output_results(MeshData mesh, int tri_index, vec3 hit)
{
	tri_buffer = mesh.tri_buffer;
	vert_buffer = mesh.vert_buffer;
	norm_buffer = mesh.norm_buffer;

	float u = hit.y;
	float v = hit.z;

	Triangle triangle;
	fetch_triangle(tri_index, triangle);

	vec3 pos = texelFetch(vert_buffer, triangle.v0 + triangle.pad).xyz * (1-u-v);
	pos += texelFetch(vert_buffer, triangle.v1 + triangle.pad).xyz * u;
	pos += texelFetch(vert_buffer, triangle.v2 + triangle.pad).xyz* v;

	vec3 norm = texelFetch(norm_buffer, triangle.v0 + triangle.pad).xyz * (1-u-v);
	norm += texelFetch(norm_buffer, triangle.v1 + triangle.pad).xyz * u;
	norm += texelFetch(norm_buffer, triangle.v2 + triangle.pad).xyz* v;

	vec3 L = normalize(vec3(3.0, -4.0, 6.0) - pos);
	vec3 N = normalize(norm);

	out_color = vec3(dot(N, L) * 0.8);
}

struct DDAData {
	vec3 aabb[2];
	vec3 resolution;
	vec3 cell_size;
	vec3 tmax;
	vec3 tstep;
	ivec3 coord_step;

	ivec3 coord;
	float t;
};

void dda_init(inout DDAData dda, vec3 aabb[2], vec3 resolution)
{
	dda.aabb = aabb;
	dda.resolution = resolution;
	dda.cell_size = (aabb[1] - aabb[0]) / resolution;
}

bool dda_ray_to_bounds(inout DDAData dda, inout vec3 ray_origin, vec3 ray_dir, vec3 ray_inv, out float tmin)
{
	vec3 ray_sign = step(0.0, -ray_inv);
	vec3 bounds = dda.aabb[1] * ray_sign + dda.aabb[0] * (ivec3(1) - ray_sign);
	vec3 t_vmin = (bounds - ray_origin) * ray_inv;
	bounds = dda.aabb[0] * ray_sign + dda.aabb[1] * (ivec3(1) - ray_sign);
	vec3 t_vmax = (bounds - ray_origin) * ray_inv;

	if (any(greaterThan(t_vmin.xyxz, t_vmax.yxzx)))
		return false;

	tmin = max(max(t_vmin.x, t_vmin.y), t_vmin.z);
	float tmax = min(min(t_vmax.x, t_vmax.y), t_vmax.z);

	if (tmax <= tmin)
		return false;

	ray_origin += ray_dir * (tmin + epsilon);
	return true;
}

void dda_traversal_init(inout DDAData dda, vec3 ray_origin, vec3 ray_direction, vec3 ray_inverse)
{
	dda.coord = ivec3(floor((ray_origin - dda.aabb[0]) / dda.cell_size));
	vec3 ray_sign = step(0.0, -ray_inverse);
	vec3 cell_min = dda.coord * dda.cell_size + dda.aabb[0];
	vec3 cell_max = (dda.coord + vec3(1)) * dda.cell_size + dda.aabb[0];
	vec3 bounds = cell_min * ray_sign + cell_max * (ivec3(1) - ray_sign);
	dda.tmax = (bounds - ray_origin) * ray_inverse;
	dda.coord_step = ivec3(sign(ray_direction));
	dda.tstep = dda.cell_size * dda.coord_step * ray_inverse;
	dda.t = min(min(dda.tmax.x, dda.tmax.y), dda.tmax.z);
}

void dda_traversal_step(inout DDAData dda)
{
	ivec3 mask = ivec3(step(-dda.t, -dda.tmax));
	dda.coord += mask * dda.coord_step;
	dda.tmax += mask * dda.tstep;
	dda.t = min(min(dda.tmax.x, dda.tmax.y), dda.tmax.z);
}

bool dda_in_bounds(DDAData dda)
{
	return !any(lessThan(dda.coord, ivec3(0))) && !any(greaterThan(dda.coord, ivec3(dda.resolution-1)));
}

void main()
{
	out_color = vec3(0.2);
	vec3 ray_d = normalize(in_ray_d);
	vec3 ray_inv = vec3(1.0) / ray_d;

	int closest_mesh_id = -1;
	int closest_tri_id = -1;
	vec3 closest_hit = vec3(1000, 0, 0);

	DDAData scene_dda;
	dda_init(scene_dda, scene_aabb, scene_resolution);
	float unused;
	vec3 ray_copy = vec3(in_ray_o);
	if (!dda_ray_to_bounds(scene_dda, ray_copy, ray_d, ray_inv, unused))
		return;
	dda_traversal_init(scene_dda, ray_copy, ray_d, ray_inv);

	int scene_width = imageSize(scene_list).x;
	while (dda_in_bounds(scene_dda)) {
		uint scene_ptr = imageLoad(scene_voxels, scene_dda.coord).r;

		// for (int i = 0; i < num_meshes; ++i) {
		while (scene_ptr != LIST_END) {
			uvec2 scene_link = imageLoad(scene_list, ivec2(scene_ptr % scene_width, scene_ptr / scene_width)).rg;
			scene_ptr = scene_link.y;
			int i = int(scene_link.x);
			vec3 ray_o = in_ray_o;
			MeshData mesh = mesh_buffer[i];
			vec3 aabb[2];
			aabb[0] = mesh.aabb[0].xyz;
			aabb[1] = mesh.aabb[1].xyz;
			int list_width = imageSize(mesh.voxel_list).x;
			tri_buffer = mesh.tri_buffer;
			vert_buffer = mesh.vert_buffer;
			norm_buffer = mesh.norm_buffer;
			num_triangles = int(mesh.voxel_resolution.w);

			DDAData mesh_dda;
			dda_init(mesh_dda, aabb, mesh.voxel_resolution.xyz);

			// Make sure we are in the voxel region
			float tmin;
			if (!dda_ray_to_bounds(mesh_dda, ray_o, ray_d, ray_inv, tmin))
				continue;

			// Initialize DDA traversal variables
			dda_traversal_init(mesh_dda, ray_o, ray_d, ray_inv);

			// Traverse voxel grid
			while (dda_in_bounds(mesh_dda)) {
				uint ptr = imageLoad(mesh.voxel_data, mesh_dda.coord).r;

				int tri_index;
				vec3 hit;
				if (trace_list(ptr, mesh.voxel_list, list_width, ray_o, ray_d, mesh_dda.t, tri_index, hit)) {
					float dist = hit.x + tmin + epsilon;
					if (dist > 0 && dist < closest_hit.x)
					{
						closest_mesh_id = i;
						closest_tri_id = tri_index;
						closest_hit = vec3(dist, hit.yz);
					}
					break;
				}

				dda_traversal_step(mesh_dda);
			}
		}
		dda_traversal_step(scene_dda);
	}

	if (closest_mesh_id != -1)
	{
		output_results(mesh_buffer[closest_mesh_id], closest_tri_id, closest_hit);
	}
}
