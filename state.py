import ctm


class State(object):
	def __init__(self):
		#"Current transform matrix"
		self.ctm = ctm.CTM()

		#Note: this is apparently not saved by attrib begin and end
		self.defnode_name = None

		self._stack = []

	def push(self):
		self._stack.append( self.ctm.get_copy() )
	def push_transform(self):
		self._stack.append( self.ctm.get_copy() )
	def pop(self):
		self.ctm = self._stack.pop()
	def pop_transform(self):
		self.ctm = self._stack.pop()

	def get_copy(self):
		result = State()
		result.ctm = self.ctm.get_copy()
		result.defnode_name = self.defnode_name
		for ctm in self._stack:
			result._stack.append(ctm.get_copy())
		return result

	def begin_defer(self, name):
		assert self.defnode_name == None
		self.defnode_name = name
	def end_defer(self):
		assert self.defnode_name != None
		self.defnode_name = None
