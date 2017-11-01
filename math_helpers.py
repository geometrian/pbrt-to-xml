def rndint(x):
	return int(round(x))

#Manual matrix code so that `numpy` won't be a dependency.
#	Note: adapted from https://stackoverflow.com/a/39881366/688624
#	Transpose
def matr_transpose(m):
	result = []
	for r in range(len(m)):
		row = []
		for c in range(len(m[r])):
			if c==r: row.append(m[r][c])
			else:    row.append(m[c][r])
		result.append(row)
	return result
#	Minor
def matr_minor(m, i,j):
	return [row[:j] + row[j+1:] for row in (m[:i]+m[i+1:])]
#	Determinant
def matr_det(m):
	if len(m) > 2:
		det = 0
		for c in range(len(m)): det+=((-1)**c)*m[0][c]*matr_det(matr_minor(m,0,c))
		return det
	else:
		return m[0][0]*m[1][1]-m[0][1]*m[1][0]
def matr_inv(m):
	determinant = matr_det(m)
	if len(m) > 2:
		cofactors = []
		for r in range(len(m)):
			cofactorRow = []
			for c in range(len(m)):
				minor = matr_minor(m,r,c)
				cofactorRow.append(((-1)**(r+c)) * matr_det(minor))
			cofactors.append(cofactorRow)
		cofactors = matr_transpose(cofactors)
		for r in range(len(cofactors)):
			for c in range(len(cofactors)):
				cofactors[r][c] = cofactors[r][c]/determinant
		return cofactors
	else:
		return [ [m[1][1]/determinant, -1*m[0][1]/determinant], [-1*m[1][0]/determinant, m[0][0]/determinant] ]
