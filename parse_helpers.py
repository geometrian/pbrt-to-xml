def parse_array(tokenstream):
	_ = tokenstream.pop_next()
	assert _ == "["
	result = []
	while True:
		token = tokenstream.pop_next()
		if token == "]": break
		result.append(token)
	return result

def parse_varfunction(tokenstream, identifier, scene):
	identifier_type = tokenstream.pop_next()[1:-1]
	params = {}
	while tokenstream.peek()[0] == "\"":
		type_and_name = tokenstream.pop_next()[1:-1]
		if tokenstream.peek() == "[":
			params[type_and_name] = parse_array(tokenstream)
		else:
			params[type_and_name] = tokenstream.pop_next()
	return [identifier,identifier_type,params]
