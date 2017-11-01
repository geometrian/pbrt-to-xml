class TransformBase(object):
	def __init__(self, string):
		self.string = string
	def write(self, file, line_prefix):
		for line in self.string.split("\n"):
			file.write(line_prefix+line+"\n")
	def __hash__(self):
		return hash(self.transform)
	def __eq__(self, other):
		return self.transform == self.transform
	def __ne__(self, other):
		return not self == other
class LookAt(TransformBase):
	def __init__(self, x,y,z, cx,cy,cz, ux,uy,uz):
		TransformBase.__init__(
			self,
"""<lookat
	x="%g" y="%g" z="%g"
	cx="%g" cy="%g" cz="%g"
	ux="%g" uy="%g" uz="%g"
/>"""% (x,y,z, cx,cy,cz, ux,uy,uz)
		)
		self.transform = ( x,y,z, cx,cy,cz, ux,uy,uz )
	def is_iden(self):
		return False #TODO: better
class Rotate(TransformBase):
	def __init__(self, degrees, x,y,z):
		TransformBase.__init__(
			self,
			"<rotate degrees=\"%g\" rx=\"%g\" ry=\"%g\" rz=\"%g\"/>"%(degrees,x,y,z)
		)
		self.transform = ( degrees, x,y,z )
	def is_iden(self):
		return self.transform[0] % 360.0 == 0.0
class Scale(TransformBase):
	def __init__(self, sx,sy,sz):
		TransformBase.__init__(
			self,
			"<scale sx=\"%g\" sy=\"%g\" sz=\"%g\"/>"%(sx,sy,sz)
		)
		self.transform = ( sx,sy,sz )
	def is_iden(self):
		return self.transform == ( 1,1,1 )
class Transform(TransformBase):
	def __init__(self, transform):
		#Transpose input
		transform2 = [ None ]*16
		for j in range(4):
			for i in range(4):
				i_src = i*4 + j
				i_dst = j*4 + i
				transform2[i_dst] = transform[i_src]

		matrix = [[None for i in range(4)] for j in range(4)]
		i=0; j=0
		for val in transform2:
			matrix[j][i] = val
			i += 1
			if i == 4:
				i = 0
				j += 1
		s = "<transform"
		for j in range(4):
			for i in range(4):
				s += " m%d%d=\"%g\"" % (j,i,matrix[j][i])
		s += "/>"

		TransformBase.__init__(self,s)
		self.transform = tuple(transform2)
	def is_iden(self):
		return self.transform == ( 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 )
	def _fits(self, pattern):
		for i in range(16):
			if pattern[i]==None: continue
			if self.transform[i]!=pattern[i]: return False
		return True
	def interpret(self):
		if self._fits(( None,0,0,0, 0,None,0,0, 0,0,None,0, 0,0,0,1 )): return Scale( self.transform[0], self.transform[4+1], self.transform[4+4+2] )
		if self._fits(( 1,0,0,None, 0,1,0,None, 0,0,1,None, 0,0,0,1 )): return Translate( self.transform[3], self.transform[4+3], self.transform[4+4+3] )
		return self
class Translate(TransformBase):
	def __init__(self, tx,ty,tz):
		TransformBase.__init__(
			self,
			"<translate tx=\"%g\" ty=\"%g\" tz=\"%g\"/>"%(tx,ty,tz)
		)
		self.transform = ( tx,ty,tz )
	def is_iden(self):
		return self.transform == ( 0,0,0 )

class CTM(object):
	def __init__(self):
		self._stack = []

	def __add__(self, other):
		result = CTM()
		result._stack = list(self._stack) + list(other._stack)
		return result

	def clear(self):
		self._stack = []

	def get_copy(self):
		result = CTM()
		result._stack = list(self._stack)
		return result

	def erase_prefix(self, other):
		self._stack = self._stack[len(other._stack):]
	def pop_first(self):
		self._stack = self._stack[1:]
	def kill_iden(self):
		if self._stack[-1].is_iden():
			self._stack.pop()

	def _add_to_stack(self, transform_obj):
		self._stack.append(transform_obj)
		#self._stack = [transform_obj] + self._stack
	def apply_transform(self, transform):
		transform = Transform(transform).interpret()
		self._add_to_stack(transform)
		self.kill_iden()
	def apply_lookat(self, transform):
		self._add_to_stack(LookAt(*transform))
		self.kill_iden()
	def apply_rotate(self, transform):
		self._add_to_stack(Rotate(*transform))
		self.kill_iden()
	def apply_scale(self, transform):
		self._add_to_stack(Scale(*transform))
		self.kill_iden()
	def replace(self, transform):
		transform = Transform(transform).interpret()
		self._stack = [ transform ]
		self.kill_iden()
	def apply_translate(self, transform):
		self._add_to_stack(Translate(*transform))
		self.kill_iden()

	def write(self, file, line_prefix):
		for elem in self._stack:
			elem.write(file,line_prefix)

	def __eq__(self, other):
		return self._stack == other._stack
	def __ne__(self, other):
		return not self == other
