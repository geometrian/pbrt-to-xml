import ctm
import state as state_module


num_meshes = 0
num_rawtris = 0

class ObjectBase(object):
	def __init__(self, state, string):
		self.state = state.get_copy()
		self.string = string
	def write(self, file, line_prefix):
		for line in self.string.split("\n"):
			file.write(line_prefix+line+"\n")
class Sphere(ObjectBase):
	def __init__(self, state, radius):
		global num_meshes; name="<obj-%d>"%num_meshes; num_meshes+=1
		interface = "<unknown>"
		ObjectBase.__init__(
			self, state,
"""<object type=\"sphere\" name="%s"><radius value=\"%g\"/><interface name="%s"/></object>""" % (name,radius,interface)
		)
		self.radius = radius
class PlyMesh(ObjectBase):
	def __init__(self, state, path):
		global num_meshes; name="<obj-%d>"%num_meshes; num_meshes+=1
		interface = "<unknown>"
		ObjectBase.__init__(
			self, state,
"""<object type="trimesh" name="%s" path="%s"><interface name="%s"/></object>""" % (name,path,interface)
		)
class Recurse(ObjectBase):
	def __init__(self, state, name):
		ObjectBase.__init__(
			self, state,
"<recurse name=\"%s\"/>" % name
		)
		self.recurse_name = name
class TriMesh(ObjectBase):
	def __init__(self, state, verts,indices):
		global num_rawtris
		string = ""
		for i in range(0,len(indices),3):
			i0=indices[i  ]; v0=verts[i0]
			i1=indices[i+1]; v1=verts[i1]
			i2=indices[i+2]; v2=verts[i2]
			args = (num_rawtris, v0[0],v0[1],v0[2], v1[0],v1[1],v1[2], v2[0],v2[1],v2[2], "<unknown>")
			string +=\
"<object type=\"triangle\" name=\"<raw-tri-%d>\" v0x=\"%g\" v0y=\"%g\" v0z=\"%g\" v1x=\"%g\" v1y=\"%g\" v1z=\"%g\" v2x=\"%g\" v2y=\"%g\" v2z=\"%g\"><interface name=\"%s\"/></object>" % args
			if i+3<len(indices): string+="\n"
			num_rawtris += 1
		ObjectBase.__init__(
			self, state, string
		)

class Node(object):
	def __init__(self, name):
		self.name = name

		self.transforms = []

		self.child_objects = []
		self.child_recursions = []
		self.child_nodes = []

	def write(self, file, line_prefix):
		if len(self.child_objects)>0 or len(self.child_nodes)>0:
			if self.name==None: file.write(line_prefix+"<node>\n")
			else:               file.write(line_prefix+"<node-defer name=\""+self.name+"\" disable=\"false\">\n")

			#Write node
			for transform in reversed(self.transforms):
				transform.write(file, line_prefix+"	");
			for child_object in self.child_objects + self.child_recursions:
				child_object.write(file,line_prefix+"	")
			for child_node in self.child_nodes:
				child_node.write(file, line_prefix+"	")

			if self.name==None: file.write(line_prefix+"</node>\n")
			else:               file.write(line_prefix+"</node-defer>\n")
		elif self.name != None:
			file.write(line_prefix+"<node-defer name=\""+self.name+"\" disable=\"false\"/>\n")

class Scene(object):
	def __init__(self, state):
		self.sample_count = 1 #PBRT default `16`

		self.camera_transform = None
		self.fov_deg = None

		self.objects = []

		self.state = state

		self.sensitivity = 1

	def _add_object(self, object):
		self.objects.append(object)
	def add_object_sphere(self, radius, zmin,zmax, phimax):
		self._add_object(Sphere(self.state,radius))
	def add_object_trimesh(self, verts, indices):
		self._add_object(TriMesh(self.state, verts,indices))
	def add_object_plymesh(self, path):
		self._add_object(PlyMesh(self.state,path))
	def add_recurse(self, name):
		self._add_object(Recurse(self.state,name))

	def replace_identity(self):
		self.state.ctm.clear()
	def apply_translate(self, transform):
		self.state.ctm.apply_translate(transform)
	def apply_scale(self, transform):
		self.state.ctm.apply_scale(transform)
	def apply_rotate(self, transform):
		self.state.ctm.apply_rotate(transform)
	def apply_lookat(self, transform):
		self.state.ctm.apply_lookat(transform)
	def replace_transform(self, transform):
		self.state.ctm.replace(transform)
	def apply_transform(self, transform):
		self.state.ctm.apply_transform(transform)

	def _build_hierarchy(self, objects,name):
		if len(objects) > 0:
			node = Node(name)
			while True:
				#See if we have any objects with no remaining transforms on them (i.e., they're
				#	happy in the currently transformed node)

				found_empty = False
				for object in objects:
					if len(object.state.ctm._stack) == 0:
						found_empty = True
						break

				if found_empty:
					#If we do, then add them to the current node, add the remaining objects
					#	recursively, and we're done.

					#		Should make sure we don't recurse twice to the same object, because
					#			that'd be pointless and wasteful (some PBRT files do this,
					#			presumably erroneously).
					recursed_to = set()

					objects_remaining = []
					for object in objects:
						if len(object.state.ctm._stack) == 0:
							if hasattr(object,"recurse_name"):
								if object.recurse_name not in recursed_to:
									node.child_recursions.append(object)
									recursed_to.add(object.recurse_name)
							else:
								node.child_objects.append(object)
						else:
							objects_remaining.append(object)
					child_node = self._build_hierarchy(objects_remaining,None)
					if child_node!=None: node.child_nodes.append(child_node)
					break
				else:
					#If we don't, then every object has at least one more transform.  Figure out
					#	how many different initial transforms there are.

					first_transforms = {}
					for object in objects:
						key = object.state.ctm._stack[0]
						if key not in first_transforms:
							first_transforms[key] = []
						first_transforms[key].append(object)
					assert len(first_transforms) > 0

					if len(first_transforms) == 1:
						#	If there's only one unique initial transform all objects share, apply
						#		it to the node and loop back around to check all the objects again.
						node.transforms.append( objects[0].state.ctm._stack[0] )
						for object in objects:
							object.state.ctm.pop_first()
					else:
						#	Otherwise, group the objects by their initial transforms, append each
						#		group separately and recursively, and we're done.
						for obj_list in first_transforms.values():
							child_node = self._build_hierarchy(obj_list,None)
							if child_node!=None: node.child_nodes.append(child_node)
						break

			return node
		else:
			return None
	def write_xml(self, file, dir,path_in,path_out):
		#XML file beginning
		file.write(
"""<xml>
	<scene>
		<!--
			Auto-converted scenefile:
				PBRT in:     "%s"
				libmcrt out: "%s"
		-->
""" % (path_in,path_out)
		)

		#Nodes
		#	Separate the normal and the deferred objects
		normal_objects = []
		deferred_objects = {}
		for object in self.objects:
			if object.state.deferred_name != None:
				if object.state.deferred_name not in deferred_objects:
					deferred_objects[object.state.deferred_name] = []
				deferred_objects[object.state.deferred_name].append(object)
			else:
				normal_objects.append(object)
		#	Unroll the deferred nodes; PBRT's instantiation of deferred nodes post-transforms the
		#		objects, and this makes storing transforms more difficult.
		for object_name in deferred_objects.keys():
			for object in deferred_objects[object_name]:
				object.post_transformers = []
		for object in normal_objects:
			if hasattr(object,"recurse_name"):
				for deferred_obj in deferred_objects[ object.recurse_name ]:
					deferred_obj.post_transformers.append( object )
		#		Remove unused deferred nodes
		for object_name in deferred_objects.keys():
			deferred_objects[object_name] = [object for object in deferred_objects[object_name] if len(object.post_transformers)>0]
		for object_name in deferred_objects.keys():
			if len(deferred_objects[object_name])==0: del deferred_objects[object_name]
		#	Build hierarchies for the deferred objects
		deferred_nodes = []
		if len(deferred_objects) > 0:
			file.write("\n		<!-- Deferred Objects -->\n")
			for name in deferred_objects:
				node = self._build_hierarchy(deferred_objects[name],name)
				if node!=None: deferred_nodes.append(node)
		#	Write the normal objects
		file.write("\n		<!-- Main Scene -->\n")
		normal_node = self._build_hierarchy(normal_objects,None)
		for node in deferred_nodes:
			node.write(file,"		")
		normal_node.write(file,"		")

		file.write(
"""
		<!-- Lights -->
		<node>
			<object type="point" name="pointLight">
				<interface name="mtl-point-lgt"/>
				<position x="0" y="0" z="22"/>
			</object>
		</node>
"""
		)

		#Camera
		file.write(
"""
		<!-- Camera -->
		<node>
			<scale sx="-1" sy="1" sz="1"/>
"""
		)
		self.camera_transform.write(file,"			")
		file.write(
"""			<camera>
				<aperture type="point"><position value="0"/></aperture>
				<sensor>
					<position fov-degrees-"""
		)
		if self.res[0] < self.res[1]: file.write("x")
		else:                         file.write("y")
		file.write("""="%g"/>
""" % self.fov_deg
		)
		file.write(
"""					<size-y value="1"/>
					<width value="%d"/>
					<height value="%d"/>
""" % self.res
		)
		if hasattr(self,"rect"):
			file.write(
"""					<rect x=\"%d\" y=\"%d\" w=\"%d\" h=\"%d\"/>
""" % self.rect
			)
		file.write( #TODO: don't ignore reconstruction type
"""					<sensitivity value="%g"/>
					<reconstruction type="mitchell-netravali"/>
				</sensor>
				<frames>
					<frame name="0" t0="0.000" t1="1.000"/>
				</frames>
			</camera>
		</node>
""" % self.sensitivity
		)

		#Materials
		file.write(
"""
		<!-- Materials -->
		<interface-stack name="mtl-point-lgt">
			<edf type="lambert"><spectrum value="500.0"><cie-illuminant type="E"/></spectrum></edf>
			<bsdf type="delta"/>
		</interface-stack>
		<interface-stack name="<unknown>">
			<bsdf>
				<brdf type="lambert"><diffuse r="1" g="1" b="1"/></brdf>
				<btdf/>
			</bsdf>
		</interface-stack>
"""
		)

		#Accel type
		file.write(
"""
		<!-- Acceleration Structure -->
		<accel type=\"LBVH-2\"/>
"""
		)

		file.write("	</scene>\n")

		#Integrator
		file.write(
"""
	<!-- Integrator -->
	<integrator type="normals" absolute="true">
		<max-depth-eye value="6"/>
		<color-miss r="1" g="0" b="1"/>
		<sample-pixels type="centered" value="%d"/>
	</integrator>
""" % self.sample_count
		)

		file.write("</xml>")
