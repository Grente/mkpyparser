# -*- coding: utf-8 -*-

# language=bnf
"""
// 文法定义（忽略空格和制表符）：
模板代码		::= 语句 ( "\\n" 语句 ) *
语句		::= 变量名称 "=" 值
值		::= 表格列 | 字典 | 列表 | 元组
字典		::= "{" ( 表格列 | 仅含列元组 ) ":" 值 "}"
列表		::= "[" ( 表格列 | 仅含列元组 ) "]"
元组		::= "(" 元组元素 ( "," 元组元素 ) * ")"
元组元素		::= 表格列 | 列表 | 字典 | 元组
仅含列元组	::= "(" 仅含列元组元素 ( "," 仅含列元组元素 ) * ")"
仅含列元组元素	::= 表格列 | 仅含列元组
表格列		::= "<" 表格列元素 ">"
表格列元素	::= 表格列名 | (函数名 "(" [表格列元素 ("," 表格列元素) *] ")" )
表格列名		::= < 仅由中英文数字字符组成，至少一个字符 >
函数名		::= < [A-z_][A-z0-9_]* >
变量名称		::= < [A-z_][A-z0-9_]* >
"""
# language=markdown
"""
## 总结
1. list里只能放表格列或者仅由表格列嵌套起来的tuple
	例如 [<Col>] 或 [ (<Col1>, ( <Col2>, <Col3>) ) ] 是可行的
	但是 [ {<Col1>: <Col2>} ] 或 [[<Col1>]] 或 [(<Col1>, [<Col2>])] 是不行的 
2. dict的值可以放表格列、dict、list、tuple。dict的键只能放表格列或仅由表格列嵌套起来的元组
	例如 {<Col1>: <Col2>}, {<Col1>: (<Col2>, )}, {<Col1>: [<Col2>]}, {<Col1>: {<Col2>: <Col3>}}
		{(<Col1>, <Col2>): <Col3>}, {(<Col1>, (<Col2>, <Col3>)): <Col4>} 都是可行的
	但是 {[<Col1>]: <Col2>}, {{<Col1>: <Col2>}: <Col3>}, {(<Col1>, [<Col2>]): <Col3>} 是不行的
3. 在没有1和2的限制情况下，tuple里可以放任意的表格列、dict、list、tuple
正常情况下的导表逻辑是不会涉及到1和2的限制的，所以平常用不需要去了解这里的限制
"""

__all__ = ["Parse"]

import re
import threading
import __builtin__ as builtins

STR_TYPES = (str, unicode)
NUM_TYPES = (int, long, float)

TOKEN_VAR = 1
TOKEN_EQUALS = 2
TOKEN_NEWLINE = 3
TOKEN_TAB = 4
TOKEN_COMMA = 5
TOKEN_COLON = 6
TOKEN_TUPLE_LEFT = 7
TOKEN_TUPLE_RIGHT = 8
TOKEN_LIST_LEFT = 9
TOKEN_LIST_RIGHT = 10
TOKEN_DICT_LEFT = 11
TOKEN_DICT_RIGHT = 12
TOKEN_COL_LEFT = 13
TOKEN_COL_RIGHT = 14

SYMBLE2TOKENTYPE = {
	"\t": TOKEN_TAB,
	"\n": TOKEN_NEWLINE,
	",": TOKEN_COMMA,
	":": TOKEN_COLON,
	"=": TOKEN_EQUALS,
	"(": TOKEN_TUPLE_LEFT,
	")": TOKEN_TUPLE_RIGHT,
	"[": TOKEN_LIST_LEFT,
	"]": TOKEN_LIST_RIGHT,
	"{": TOKEN_DICT_LEFT,
	"}": TOKEN_DICT_RIGHT,
	"<": TOKEN_COL_LEFT,
	">": TOKEN_COL_RIGHT,
}


def tokenize(code):
	tokens = []
	word = ""
	for c in code:
		if c in (' ',):
			if word:
				tokens.append((TOKEN_VAR, word))
				word = ""
		elif c in SYMBLE2TOKENTYPE:
			if word:
				tokens.append((TOKEN_VAR, word))
				word = ""
			tokens.append((SYMBLE2TOKENTYPE[c], c))
		else:
			word += c
	return tokens


def showTokens(tokens):
	return ''.join([i[1] for i in tokens])


def tokensTrim(tokens):
	while tokens and tokens[0][0] in (TOKEN_TAB, TOKEN_NEWLINE):
		tokens.pop(0)
	while tokens and tokens[-1][0] in (TOKEN_TAB, TOKEN_NEWLINE):
		tokens.pop(-1)
	return


g_ThreadData = {}  # {threadid: data}  # 支持多线程


def getThreadData():
	global g_ThreadData
	tid = threading.currentThread()
	if tid not in g_ThreadData:
		g_ThreadData[tid] = {}
	return g_ThreadData[tid]


def getFunction(name):
	if not name:
		return lambda x: x
	upper_mod = getThreadData()['uppermodule']
	if upper_mod and name in upper_mod and callable(upper_mod[name]):
		return upper_mod[name]
	if name in globals() and callable(globals()[name]):
		return globals()[name]
	fn = getattr(builtins, name, None)
	if fn and callable(fn):
		return fn
	raise Exception("找不到函数 %s" % name)


def int(x):
	if x is None:
		return 0
	if isinstance(x, STR_TYPES):
		if '.' in x:
			return builtins.int(builtins.float(x))
		return builtins.int(x)
	if isinstance(x, float):
		return builtins.int(x)
	if isinstance(x, bool):
		return 1 if x else 0
	return builtins.int(x)


def exportCellToStr(cell, col_node_inst):
	if col_node_inst.m_FnName:
		cell = getFunction(col_node_inst.m_FnName)(cell)
	else:
		if isinstance(cell, STR_TYPES):
			if re.match("^[0-9]+$", cell):
				cell = int(cell)
			if re.match("^[0-9]+\\.0+$", cell):
				cell = int(cell[: cell.find('.')])
	if isinstance(cell, builtins.int):
		return str(cell)
	if isinstance(cell, builtins.float):
		if cell == int(cell):
			return str(int(cell))
		return str(cell)
	if isinstance(cell, bool):
		return "1" if cell else "0"
	if cell is None:
		return "0"
	return "\"%s\"" % cell


class CNode:
	def Parse(self, tokens):
		raise NotImplementedError

	def GenCode(self, sub_table):
		raise NotImplementedError


class CEmptyNode(CNode):
	def Parse(self, tokens):
		return tokens

	def GenCode(self, sub_table):
		return ""


STATEMENT_COMMENT_TEMPLATE = \
'''\

"""
\t%s %s
%s
"""
%s
'''


class CParseError(Exception):
	def __init__(self, msg, tokens):
		self.m_Msg = msg
		self.m_Tokens = tokens

	def __str__(self):
		return self.m_Msg

	def __repr__(self):
		return self.m_Msg


class CCompileError(Exception):
	pass


class CGrammarNode(CNode):
	def __init__(self):
		self.m_Tokens = []
		self.m_Elements = []

	def Parse(self, tokens):
		tokensTrim(tokens)
		while len(tokens) > 0:
			node = CStatementNode()
			after_tokens = node.Parse(tokens)
			self.m_Tokens.append(tokens[0: len(tokens) - len(after_tokens)])
			tokens = after_tokens
			self.m_Elements.append(node)

	def GenCode(self, sub_table):
		reslst = []
		for i, node in enumerate(self.m_Elements):
			reslst.append(STATEMENT_COMMENT_TEMPLATE % (
				sub_table.m_TableName,
				sub_table.m_SheetName,
				'\n'.join(['\t' + i for i in showTokens(self.m_Tokens[i]).split('\n')]),
				node.GenCode(sub_table.GetSubTable([], 0, sub_table.m_Rows))
			))
		return '\n\n'.join(reslst)


class CStatementNode(CNode):
	def __init__(self):
		self.m_VarName = ""
		self.m_Value = None

	def Parse(self, tokens):
		tokensTrim(tokens)
		if tokens[0][0] != TOKEN_VAR:
			raise CParseError("需要变量名", tokens)
		self.m_VarName = tokens[0][1]
		tokens = tokens[1:]
		tokensTrim(tokens)
		if tokens[0][0] != TOKEN_EQUALS:
			raise CParseError("需要等号", tokens)
		tokens.pop(0)
		tokensTrim(tokens)
		if tokens[0][0] in TOKENTYPE2NODECLASS:
			self.m_Value = TOKENTYPE2NODECLASS[tokens[0][0]]()
			tokens = self.m_Value.Parse(tokens)
		else:
			raise CParseError("需要数据", tokens)
		return tokens

	def GenCode(self, sub_table):
		return "%s = %s" % (self.m_VarName, self.m_Value.GenCode(sub_table))


class CDictDataNode(CNode):
	def __init__(self):
		self.m_Key = []
		self.m_Value = None
		self.m_Prefix = ""
		self.m_Suffix = ""

	def Parse(self, tokens):
		tokensTrim(tokens)
		if tokens[0][0] != TOKEN_DICT_LEFT:
			raise CParseError("需要{", tokens)
		tokens.pop(0)
		while tokens[0][0] in (TOKEN_NEWLINE, TOKEN_TAB):
			self.m_Prefix += tokens[0][1]
			tokens.pop(0)
		tokensTrim(tokens)
		if tokens[0][0] == TOKEN_DICT_RIGHT:
			tokens.pop(0)
			self.m_Value = CEmptyNode()
			return tokens
		if tokens[0][0] == TOKEN_COL_LEFT:
			node = CColNode()
			tokens = node.Parse(tokens)
			self.m_Key = node
		elif tokens[0][0] == TOKEN_TUPLE_LEFT:
			node = CTupleDataNode(True)
			tokens = node.Parse(tokens)
			self.m_Key = node
		else:
			raise CParseError("需要列名或者元组", tokens)
		tokensTrim(tokens)
		if tokens[0][0] != TOKEN_COLON:
			raise CParseError("需要:", tokens)
		tokens.pop(0)
		tokensTrim(tokens)
		if tokens[0][0] in TOKENTYPE2NODECLASS:
			self.m_Value = TOKENTYPE2NODECLASS[tokens[0][0]]()
			tokens = self.m_Value.Parse(tokens)
		else:
			raise CParseError("需要数据", tokens)
		while tokens[0][0] in (TOKEN_NEWLINE, TOKEN_TAB):
			self.m_Suffix += tokens[0][1]
			tokens.pop(0)
		if tokens[0][0] == TOKEN_COMMA:
			tokens.pop(0)
			self.m_Suffix = ""
			while tokens[0][0] in (TOKEN_NEWLINE, TOKEN_TAB):
				self.m_Suffix += tokens[0][1]
				tokens.pop(0)
		if tokens[0][0] != TOKEN_DICT_RIGHT:
			raise CParseError("需要}", tokens)
		tokens.pop(0)
		return tokens

	def GenCode(self, sub_table):
		res = "{"
		keydct = self.getKeys(sub_table)
		self.validKeys(keydct.values())
		ordered_key_rows = sorted(keydct.keys())
		exclude_cols = self.getAllKeysNames(self.m_Key)
		ordered_key_rows.append(sub_table.m_Rows)
		for i in range(len(ordered_key_rows) - 1):
			t = sub_table.GetSubTable(exclude_cols, ordered_key_rows[i], ordered_key_rows[i + 1])
			valcode = self.m_Value.GenCode(t)
			key_text = keydct[ordered_key_rows[i]]
			if isinstance(key_text, (list, tuple)):
				key_text = "(%s, )" % (', '.join(key_text))
			res += "%s%s: %s, " % (self.m_Prefix, key_text, valcode)
		res += "%s}" % self.m_Suffix
		return res

	def validKeys(self, keyvalues):
		d = {}
		for i in keyvalues:
			if i not in d:
				d[i] = 0
			d[i] += 1
			if d[i] > 1:
				raise CCompileError("导表dict键重复: %s" % i)

	def getKeys(self, sub_table):
		if isinstance(self.m_Key, CColNode):
			col_data = self.m_Key.GetColData(sub_table)
			return col_data
		if isinstance(self.m_Key, CTupleDataNode):
			return self.m_Key.GetColData(sub_table)

	def getAllKeysNames(self, keys):
		if isinstance(keys, CColNode):
			return keys.GetAllColNames()
		lst = []
		for node in keys.m_Element:
			lst.extend(self.getAllKeysNames(node))
		return lst


class CTupleDataNode(CNode):
	def __init__(self, only_col_and_tuple_nested=False):
		self.m_OnlyColAndTupleNested = only_col_and_tuple_nested
		self.m_Prefix = []
		self.m_Element = []
		self.m_Suffix = ""

	def Parse(self, tokens):
		tokensTrim(tokens)
		if tokens[0][0] != TOKEN_TUPLE_LEFT:
			raise CParseError("需要(", tokens)
		tokens.pop(0)
		while len(tokens) > 0:
			prefix = ""
			while tokens[0][0] in (TOKEN_NEWLINE, TOKEN_TAB):
				prefix += tokens[0][1]
				tokens.pop(0)
			if tokens[0][0] == TOKEN_TUPLE_RIGHT:
				self.m_Suffix = prefix
				tokens.pop(0)
				break
			self.m_Prefix.append(prefix)
			if tokens[0][0] == TOKEN_TUPLE_LEFT:
				node = CTupleDataNode(self.m_OnlyColAndTupleNested)
				tokens = node.Parse(tokens)
				self.m_Element.append(node)
			elif tokens[0][0] == TOKEN_COL_LEFT or \
					tokens[0][0] in TOKENTYPE2NODECLASS and not self.m_OnlyColAndTupleNested:
				node = TOKENTYPE2NODECLASS[tokens[0][0]]()
				tokens = node.Parse(tokens)
				self.m_Element.append(node)
			else:
				raise CParseError("需要数据", tokens)
			prefix = []
			while tokens[0][0] in (TOKEN_NEWLINE, TOKEN_TAB):
				prefix.append(tokens[0])
				tokens.pop(0)
			if tokens[0][0] not in (TOKEN_COMMA, TOKEN_TUPLE_RIGHT):
				raise CParseError("需要,或)", tokens)
			if tokens[0][0] == TOKEN_COMMA:
				tokens.pop(0)
			else:
				tokens = prefix + tokens
		return tokens

	def GenCode(self, sub_table):
		res = "("
		for i, ele in enumerate(self.m_Element):
			if isinstance(ele, CColNode):
				res += "%s%s, " % (
					self.m_Prefix[i],
					ele.GenCode(sub_table)
				)
			elif isinstance(ele, (CTupleDataNode, CDictDataNode, CListDataNode)):
				res += "%s%s, " % (self.m_Prefix[i], ele.GenCode(sub_table))
		res += "%s)" % self.m_Suffix
		return res

	def GetColData(self, sub_table):
		if not self.m_OnlyColAndTupleNested:
			raise Exception("只允许m_OnlyColAndTupleNested为True的情况下调用该方法")
		res = {}
		rows = set()
		d = []
		for idx, ele in enumerate(self.m_Element):
			coldata = ele.GetColData(sub_table)
			d.append(coldata)
			rows = rows.union(coldata.keys())
		for row in sorted(rows):
			t = []
			for coldata in d:
				t.append(coldata[row] if row in coldata else None)
			if all([i is None for i in t]):
				continue
			res[row] = tuple(t)
		return res


class CListDataNode(CNode):
	def __init__(self):
		self.m_Element = None
		self.m_Prefix = ""
		self.m_Suffix = ""

	def Parse(self, tokens):
		tokensTrim(tokens)
		if tokens[0][0] != TOKEN_LIST_LEFT:
			raise CParseError("需要[", tokens)
		tokens.pop(0)
		while tokens[0][0] in (TOKEN_NEWLINE, TOKEN_TAB):
			self.m_Prefix += tokens[0][1]
			tokens.pop(0)
		if tokens[0][0] == TOKEN_TUPLE_LEFT:
			node = CTupleDataNode(True)
			tokens = node.Parse(tokens)
			self.m_Element = node
		elif tokens[0][0] == TOKEN_COL_LEFT:
			node = TOKENTYPE2NODECLASS[tokens[0][0]]()
			tokens = node.Parse(tokens)
			self.m_Element = node
		else:
			raise CParseError("需要列名或者元组", tokens)
		is_comma = False
		while tokens[0][0] in (TOKEN_NEWLINE, TOKEN_TAB, TOKEN_COMMA):
			if tokens[0][0] == TOKEN_COMMA:
				if is_comma:
					raise CParseError("\",\"符号后应为]", tokens)
				is_comma = True
				self.m_Suffix = ""
				tokens.pop(0)
				continue
			self.m_Suffix += tokens[0][1]
			tokens.pop(0)
		if tokens[0][0] != TOKEN_LIST_RIGHT:
			raise CParseError("需要]", tokens)
		tokens.pop(0)
		return tokens

	def GenCode(self, sub_table):
		if isinstance(self.m_Element, CColNode):
			d = self.m_Element.GetColData(sub_table)
			d = [i[1] for i in sorted(d.items(), key=lambda x: x[0])]
			return "[%s%s%s]" % (
				self.m_Prefix,
				self.m_Prefix.join([i + ", " for i in d]),
				self.m_Suffix
			)
		if isinstance(self.m_Element, CTupleDataNode):
			# 获取有多少行，防止输出空行数据
			l = len(self.m_Element.GetColData(sub_table))

			res = "["
			# 如果把空行也打印的话使用 for i in range(sub_table.m_Rows):
			for i in range(l):
				t = sub_table.GetSubTable([], i, i + 1)
				res += "%s%s, " % (self.m_Prefix, self.m_Element.GenCode(t))
			res += "%s]" % self.m_Suffix
			return res


class CColNode(CNode):
	def __init__(self):
		self.m_FunctionStack = []

	def Parse(self, tokens):
		tokensTrim(tokens)
		if tokens[0][0] != TOKEN_COL_LEFT:
			raise CParseError("需要<", tokens)
		tokens.pop(0)
		tokensTrim(tokens)

		expression_tokens = []
		while len(tokens) > 0 and tokens[0][0] != TOKEN_COL_RIGHT:
			if tokens[0][0] in (TOKEN_TAB, TOKEN_NEWLINE):
				continue
			expression_tokens.append(tokens[0])
			tokens.pop(0)
			if len(tokens) == 0:
				raise CParseError("需要>", tokens)
		if len(tokens) == 0 or tokens[0][0] != TOKEN_COL_RIGHT:
			raise CParseError("需要>", tokens)
		tokens.pop(0)

		try:
			self.parseFunction(expression_tokens)
			if len(expression_tokens) > 0:
				raise CParseError("预期是>，但得到的是%s" % showTokens(expression_tokens), expression_tokens)
		except CParseError as e:
			raise CParseError("表格列描述错误：%s，错误信息：%s" % (showTokens(expression_tokens), e.m_Msg), tokens)
		return tokens

	def parseFunction(self, exp_tokens):
		token_type, token_val = exp_tokens[0]
		exp_tokens.pop(0)
		if token_type != TOKEN_VAR:
			raise CParseError("预期是函数名或表格列名，但得到的是%s" % token_val, exp_tokens)
		if len(exp_tokens) == 0 or exp_tokens[0][0] != TOKEN_TUPLE_LEFT:  # 表格列名
			self.m_FunctionStack.append(token_val)
			return
		exp_tokens.pop(0)
		attrcnt = 0
		while len(exp_tokens) > 1 and exp_tokens[0][0] != TOKEN_TUPLE_RIGHT:
			self.parseFunction(exp_tokens)
			attrcnt += 1
			if len(exp_tokens) > 0 and exp_tokens[0][0] == TOKEN_COMMA:
				exp_tokens.pop(0)
			else:
				break
		self.m_FunctionStack.append((attrcnt, getFunction(token_val)))
		if len(exp_tokens) == 0 or exp_tokens[0][0] != TOKEN_TUPLE_RIGHT:
			raise CParseError("预期是)，但得到的是%s" % (exp_tokens if exp_tokens else "空"), exp_tokens)
		exp_tokens.pop(0)

	def getVal(self, y, sub_table):
		is_all_none = True
		for i in self.m_FunctionStack:
			if isinstance(i, STR_TYPES) and sub_table.CellValue(y, i) is not None:
				is_all_none = False
				break
		if is_all_none:
			return None

		stack = []
		for i in self.m_FunctionStack:
			if isinstance(i, STR_TYPES):
				stack.append(sub_table.CellValue(y, i))
			else:
				attrcnt, fn = i
				args = []
				for j in range(attrcnt):
					args.append(stack.pop())
				args.reverse()
				stack.append(fn(*args))
		return stack[0]

	def GenCode(self, sub_table):
		val = self.getVal(0, sub_table)
		return self.exportCellToStr(val)

	def GetColData(self, sub_table):
		res = {}
		for y in range(sub_table.m_Rows):
			cell = self.getVal(y, sub_table)
			if cell is not None:
				d = self.exportCellToStr(cell)
				res[y] = d
		return res

	def exportCellToStr(self, cell):
		if len(self.m_FunctionStack) != 1:
			if isinstance(cell, STR_TYPES):
				if re.match("^[0-9]+$", cell):
					cell = int(cell)
				if re.match("^[0-9]+\\.0+$", cell):
					cell = int(cell[: cell.find('.')])
		if isinstance(cell, builtins.int):
			return str(cell)
		if isinstance(cell, builtins.float):
			if cell == int(cell):
				return str(int(cell))
			return str(cell)
		if isinstance(cell, bool):
			return "1" if cell else "0"
		if cell is None:
			return "0"
		return "\"%s\"" % cell

	def GetAllColNames(self):
		res = []
		for i in self.m_FunctionStack:
			if isinstance(i, STR_TYPES):
				res.append(i)
		return res


TOKENTYPE2NODECLASS = {
	TOKEN_COL_LEFT: CColNode,
	TOKEN_DICT_LEFT: CDictDataNode,
	TOKEN_LIST_LEFT: CListDataNode,
	TOKEN_TUPLE_LEFT: CTupleDataNode,
}


class CTableData(object):
	def __init__(self):
		self.m_TableName = None
		self.m_SheetName = None
		self.m_RawSheet = None
		self.m_Rows = None
		self.m_Cols = None
		self.m_HeaderName2ColIdx = None
		self.m_Cells = {}

	def LoadSheet(self, bk, sheet_name):
		# TODO: 记录xls表格名字, 用于异常提示
		# self.m_TableName = XXXX
		self.m_RawSheet = bk.sheet_by_name(sheet_name.decode("utf-8"))
		self.m_SheetName = sheet_name
		self.m_Rows = self.m_RawSheet.nrows
		self.m_Cols = self.m_RawSheet.ncols
		self.m_HeaderName2ColIdx = {}
		# 去掉表头数据，剩下的放m_Cells，m_Rows也-1
		for y in range(1, self.m_Rows):
			for x in range(self.m_Cols):
				d = self._cellValue(y, x)
				if d is not None:
					self.m_Cells[(y - 1, x)] = d
		for x in range(self.m_Cols):
			d = str(self._cellValue(0, x))
			d = d.lower()
			self.m_HeaderName2ColIdx[d] = x
		self.m_Rows -= 1

	def _cellValue(self, y, x):
		if isinstance(x, str):
			x = self.m_HeaderName2ColIdx[x]
		d = self.m_RawSheet.cell_value(y, x)
		if isinstance(d, STR_TYPES) and len(d) == 0:
			return None
		if isinstance(d, unicode):
			try:
				d = d.encode("utf-8")
			except:
				raise Exception("错误的字符串,%s(%d,%d): %s" % (
					self.m_RawSheet.name.encode("utf-8"), y, x, d.encode("utf-8")))
		return d

	def CellValue(self, y, x):
		if isinstance(x, str):
			x = self.m_HeaderName2ColIdx[x.lower()]
		if (y, x) not in self.m_Cells:
			return None
		return self.m_Cells[(y, x)]

	def GetSubTable(self, exclude_cols, start_row=0, end_row=None):
		exclude_col_idxes = []
		for col in exclude_cols:
			exclude_col_idxes.append(self.m_HeaderName2ColIdx[col.lower()])
		if end_row is None:
			end_row = self.m_Rows
		sub_table = CTableData()
		sub_table.m_TableName = self.m_TableName
		sub_table.m_SheetName = self.m_SheetName
		sub_table.m_RawSheet = None
		sub_table.m_Rows = end_row - start_row
		sub_table.m_Cols = self.m_Cols - len(exclude_cols)
		sub_table.m_HeaderName2ColIdx = {}
		for key, val in self.m_HeaderName2ColIdx.items():
			if key.lower() not in exclude_cols:
				new_val = val - len([i for i in exclude_col_idxes if i < val])
				sub_table.m_HeaderName2ColIdx[key] = new_val
		sub_table.m_Cells = {}
		for y in range(start_row, end_row):
			real_x = 0
			for x in range(self.m_Cols):
				if x in exclude_col_idxes:
					continue
				d = self.CellValue(y, x)
				if d is not None:
					sub_table.m_Cells[(y - start_row, real_x)] = d
				real_x += 1
		return sub_table


def compileToPycode(grammar_tree, table_data):
	return grammar_tree.GenCode(table_data)


def saveCode(target_code, target_path):
	with open(target_path, "w+", encoding="utf-8") as f:
		f.write(target_code)


def tidyCode(code):
	first_ln = code.find('\n')
	if first_ln >= 0 and code[:first_ln].strip() == "":
		code = code[first_ln + 1:]
	last_ln = code.rfind('\n')
	if last_ln >= 0 and code[last_ln:].strip() == "":
		code = code[:last_ln]

	lines = code.split('\n')
	min_space = 999
	for line in lines:
		if line.strip() == "":
			continue
		space = len(line) - len(line.lstrip())
		if space < min_space:
			min_space = space

	for i in range(len(lines)):
		lines[i] = lines[i][min_space:]
	code = '\n'.join(lines)
	return code


EXPORT_TEMPLATE = """\
# -*- coding: utf-8 -*-
%s
"""


def overwriteFileToPath(path, text):
	final_text = EXPORT_TEMPLATE % text
	with open(path, 'w+') as f:
		f.write(final_text)


def Parse(bk, sheet_name, your_globals, code, target_path=None):
	getThreadData()['uppermodule'] = your_globals

	if code is None or not isinstance(code, str):
		raise Exception("Parse的code参数应为字符串")
	# 传进来的code稍微整理一下
	code = tidyCode(code)
	# 词法解析(token提取)
	tokens = tokenize(code + " ")
	# 语法解析(附带语法检查)
	tree = CGrammarNode()
	try:
		tree.Parse(tokens)
	except CParseError as e:
		msg = "模板解析错误 %s\n位置：%s" % (e, showTokens(tokens[0: -len(e.m_Tokens)]))
		raise Exception(msg)
	# 表格提取
	table_data = CTableData()
	table_data.LoadSheet(bk, sheet_name)
	# 表格数据和语法树投喂给编译器

	try:
		export_code = compileToPycode(tree, table_data)
	except CCompileError as e:
		msg = "导表错误 %s %s %s" % (table_data.m_TableName, sheet_name, e)
		raise Exception(msg)

	if target_path:
		overwriteFileToPath(target_path, export_code)
	return export_code
