# -*- coding: utf-8 -*-

import autoparser
import xlrd

PARSE_FROM_DATA_CODE_TEMPLATE = """\
# -*- coding: utf-8 -*-

#自动模板导出
%s
#自动模板导出结束

"""


def parseDatasetTemplate(bk, templatecode):
	headers = {}  # {变量名: [列名, ...]}
	sheet_name = {}  # {变量名: sheet名}

	buffer = ""
	for line in templatecode.split('\n'):
		if line.startswith("#模板定义"):
			_, var, sheet = line.replace('\t', ' ').split(' ')
			sheet_name[var] = sheet.strip()
		elif line.startswith("#模板表头"):
			attrs = line.replace('\t', ' ').split(' ')
			var = attrs[1]
			attrs = [attr for attr in attrs[2:] if attr[0].lower() != 'X']
			headers[var] = attrs
		else:
			buffer += line + '\n'
	res = []
	code_split_lst = sorted([buffer.find(i) for i in sheet_name])
	code_split_lst.append(-1)

	for idx in range(len(code_split_lst) - 1):
		part_code = buffer[code_split_lst[idx]: code_split_lst[idx + 1]]
		tokens = autoparser.tokenize(part_code + " ")
		varname = tokens[0][1]
		new_tokens = [tokens[0], ]
		header_idx = 0
		for token in tokens[1:]:
			if token[0] == autoparser.TOKEN_VAR:
				token = (autoparser.TOKEN_VAR, "<" + headers[varname][header_idx] + ">")
				header_idx += 1
			new_tokens.append(token)
		new_part_code = autoparser.showTokens(new_tokens)
		res.append(autoparser.Parse(bk, sheet_name[varname], locals(), new_part_code))
	return '\n\n'.join(res)


def templateToFile(from_path, to_path, template_coce):
	bk = xlrd.open_workbook(from_path, "utf-8")
	data_code = parseDatasetTemplate(bk, template_coce)
	f = open(to_path, "w+")
	f.write(PARSE_FROM_DATA_CODE_TEMPLATE % data_code)
	f.close()
