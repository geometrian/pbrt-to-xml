import ctm
import state as state_module


num_meshes = 0
def get_next_objname():
	global num_meshes; name="<obj-%d>"%num_meshes; num_meshes+=1
	return name

class ObjectBase(object):
	def __init__(self, name, state):
		self.name = name
		self.state = state.get_copy()
	def write(self, file, line_prefix):
		string = self.get_string()
		for line in string.split("\n"):
			file.write(line_prefix+line+"\n")
class Sphere(ObjectBase):
	def __init__(self, name, state, radius):
		ObjectBase.__init__(self,name,state)
		self.radius = radius
	def get_copy(self):
		return Sphere(self.name,self.state,self.radius)
	def get_string(self):
		return """<object type=\"sphere\" name="%s"><radius value=\"%g\"/><interface name="%s"/></object>""" % (self.name,self.radius,"<unknown>")
class Triangle(ObjectBase):
	def __init__(self, name, state, v0,v1,v2):
		ObjectBase.__init__(self,name,state)
		self.v0 = v0
		self.v1 = v1
		self.v2 = v2
	def get_copy(self):
		return Triangle(self.name,self.state,self.v0,self.v1,self.v2)
	def get_string(self):
		args = (self.name, self.v0[0],self.v0[1],self.v0[2], self.v1[0],self.v1[1],self.v1[2], self.v2[0],self.v2[1],self.v2[2], "<unknown>")
		return "<object type=\"triangle\" name=\"%s\" v0x=\"%g\" v0y=\"%g\" v0z=\"%g\" v1x=\"%g\" v1y=\"%g\" v1z=\"%g\" v2x=\"%g\" v2y=\"%g\" v2z=\"%g\"><interface name=\"%s\"/></object>" % args
class PlyMesh(ObjectBase):
	def __init__(self, name, state, path):
		ObjectBase.__init__(self,name,state)
		self.path = path
	def get_copy(self):
		return PlyMesh(self.name,self.state,self.path)
	def get_string(self):
		return """<object type="trimesh" name="%s" path="%s"><interface name="%s"/></object>""" % (self.name,self.path,"<unknown>")
class Recurse(ObjectBase):
	def __init__(self, name, state, recurse_to_defnode_name):
		ObjectBase.__init__(self,name,state)
		self.recurse_to_defnode_name = recurse_to_defnode_name
	def get_copy(self):
		return Recurse(self.name,self.state,self.recurse_to_defnode_name)
	def get_string(self):
		return "<recurse name=\"%s\"/>" % self.recurse_to_defnode_name

class Node(object):
	def __init__(self, name):
		self.name = name

		self.transforms = []

		self.child_objects = []
		self.child_recursions = []
		self.child_nodes = []

	def is_empty(self):
		if len(self.child_objects   )>0: return False
		if len(self.child_recursions)>0: return False
		if len(self.child_nodes     )>0: return False
		return True
	def write(self, file, line_prefix):
		if not self.is_empty():
			if self.name==None: file.write(line_prefix+"<node>\n")
			else:               file.write(line_prefix+"<node-defer name=\""+self.name+"\" disable=\"false\">\n")

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
		self._add_object(Sphere(get_next_objname(),self.state,radius))
	def add_object_trimesh(self, verts, indices):
		for i in range(0,len(indices),3):
			i0=indices[i  ]; v0=verts[i0]
			i1=indices[i+1]; v1=verts[i1]
			i2=indices[i+2]; v2=verts[i2]
			self._add_object(Triangle( get_next_objname(), self.state, v0,v1,v2 ))
	def add_object_plymesh(self, path):
		self._add_object(PlyMesh(get_next_objname(),self.state,path))
	def add_recurse(self, name):
		self._add_object(Recurse(get_next_objname(),self.state,name))

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
							if hasattr(object,"recurse_to_defnode_name"):
								if object.recurse_to_defnode_name not in recursed_to:
									node.child_recursions.append(object)
									recursed_to.add(object.recurse_to_defnode_name)
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
			if object.state.defnode_name != None:
				if object.state.defnode_name not in deferred_objects:
					deferred_objects[object.state.defnode_name] = []
				deferred_objects[object.state.defnode_name].append(object)
			else:
				normal_objects.append(object)

		#	Remove recursions to empty nodes
		normal_objects = [object for object in normal_objects if not hasattr(object,"recurse_to_defnode_name") or object.recurse_to_defnode_name in deferred_objects.keys()]

		#	List which instantiations--and therefore post transformations (since PBRT post-
		#		transforms objects, the motivation for most of this insanity)--every deferred
		#		object might be transformed by.
		for defnode_name in deferred_objects.keys():
			for object in deferred_objects[defnode_name]:
				object.post_transformers = []
		for object in normal_objects:
			if hasattr(object,"recurse_to_defnode_name"):
				for deferred_obj in deferred_objects[ object.recurse_to_defnode_name ]:
					deferred_obj.post_transformers.append( object )

		#		Remove unreferenced deferred nodes
		for defnode_name in deferred_objects.keys():
			deferred_objects[defnode_name] = [object for object in deferred_objects[defnode_name] if len(object.post_transformers)>0]
		for defnode_name in deferred_objects.keys():
			if len(deferred_objects[defnode_name])==0: del deferred_objects[defnode_name]

		#		Fix recursion points
		#			If there is only one instantiator for a deferred object, keep the recursion
		#			point and transforms as-is.  If there is more than one, pull the deferred
		#			object out into a new untransformed node and add new instantiators with pre-
		#			concatenated transforms.
		num_lifted_def_objs = 0
		new_deferred_objects = {}
		new_recursepts = []
		for defnode_name in deferred_objects.keys():
			for object in deferred_objects[defnode_name]:
				if len(object.post_transformers) > 1:
					new_object = object.get_copy()
					new_object.state.ctm.clear()
					new_object.state.defnode_name="<def-obj:<%d>>"%num_lifted_def_objs; num_lifted_def_objs+=1
					for post_transformer in object.post_transformers:
						new_recursept = post_transformer.get_copy()
						new_recursept.state.ctm = object.state.ctm + post_transformer.state.ctm
						new_recursept.recurse_to_defnode_name = new_object.state.defnode_name
						new_recursepts.append(new_recursept)
				else:
					#Just copy it over.  TODO: we ought to optimize the object into an actual (non-
					#	deferred) child.
					new_object = object
					new_recursepts.append(object.post_transformers[0])
				if new_object.state.defnode_name not in new_deferred_objects.keys():
					new_deferred_objects[new_object.state.defnode_name] = []
				new_deferred_objects[new_object.state.defnode_name].append(new_object)
		normal_objects = [object for object in normal_objects if not hasattr(object,"recurse_to_defnode_name")] + new_recursepts
		deferred_objects = new_deferred_objects

		#	Build hierarchies for the deferred objects
		deferred_nodes = []
		if len(deferred_objects) > 0:
			for defnode_name in deferred_objects:
				defnode = self._build_hierarchy(deferred_objects[defnode_name],defnode_name)
				if defnode!=None: deferred_nodes.append(defnode)

		#	Build hierarchy for the normal objects
		normal_node = self._build_hierarchy(normal_objects,None)

		#	Write the deferred objects
		if len(deferred_nodes) > 0:
			file.write("\n		<!-- Deferred Objects -->\n")
			for defnode in deferred_nodes:
				defnode.write(file,"		")

		#	Write the normal objects
		file.write("\n		<!-- Main Scene -->\n")
		normal_node.write(file,"		")

		#Lights
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
