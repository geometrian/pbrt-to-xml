from __future__ import print_function
import time


class TokenStream(object):
	def __init__(self):
		self.rev_tokens = []

	def add_tokens_at_current(self, tokens):
		self.rev_tokens += reversed(tokens)
	def add_tokenstream_at_current(self, tokenstream):
		self.rev_tokens += tokenstream.rev_tokens

	def peek(self):
		assert len(self.rev_tokens) >= 1
		return self.rev_tokens[-1]
	def pop_next(self, n=1):
		assert len(self.rev_tokens) >= n

		tokens = list(reversed(self.rev_tokens[-n:]))

		#self.rev_tokens = self.rev_tokens[:-n]
		for i in range(n): self.rev_tokens.pop()

		if n == 1: return tokens[0]
		else:      return list(tokens)

	def __len__(self):
		return len(self.rev_tokens)

def tokenize(lines):
	print("  Tokenizing %d lines . . ."%len(lines))

	t0 = time.time()
	tokens = []
	for i in range(len(lines)):
		line = lines[i].strip()

		token = ""
		mode = 0 #`0`:=whitespace, `1`:=word, `2`:=string
		for c in line:
			if   mode == 0:
				if   c == "#": break
				elif c.isspace(): pass
				else:
					if   c == "\"":
						mode = 2
						token += c
					elif c in ["[","]"]:
						tokens.append(c)
					else:
						mode = 1
						token += c
			elif mode == 1:
				if   c == "#": break
				elif c.isspace():
					mode = 0
					if len(token) > 0:
						tokens.append(token)
						token = ""
				else:
					token += c
			else:
				assert mode == 2
				if   c.isspace():
					token += c
				elif c == "\"":
					mode = 0
					token += c
					tokens.append(token)
					token = ""
				else:
					token += c
		if len(token) > 0:
			tokens.append(token)
		if i % 1000 == 0:
			print("\r  Tokenized line %d / %d . . ."%(i+1,len(lines)),end="")

	tokenstream = TokenStream()
	tokenstream.add_tokens_at_current(tokens)

	t1 = time.time()
	print("\r  Tokenized %d lines in %f seconds."%(len(lines),t1-t0))

	return tokenstream
