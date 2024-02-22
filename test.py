# -*- coding: utf-8 -*-

import mkpyparser.autoparser
import mkpyparser.templatemake
import xlrd


def test1():
	"""
	TEST_DATA = {
			< 法阵等级 >:(< 道具ID >, < 道具数量 >, < 备注 >),
	}
	输出：

	TEST_DATA = {

							1: (99001, 5, "备注1", ),
							2: (99001, 26, "备注2", ),
							3: (99001, 58, "备注3", ),
							4: (99001, 91, "备注4", ),
							5: (99001, 134, "备注5", ),
							6: (99001, 188, "备注6", ),
							7: (99001, 233, "备注7", ),
							8: (99001, 299, "备注8", ),
							9: (99001, 365, "备注9", ),
							10: (99001, 433, "备注10", ),
	}
	"""

	part_code = """\
TEST_DATA = {
			< 法阵等级 >:(< 道具ID >, < 道具数量 >, < 备注 >),
}
"""
	bk = xlrd.open_workbook("./测试导表.xls".decode("utf-8").encode("GBK"), "utf-8")
	print mkpyparser.autoparser.Parse(bk, "页签1", locals(), part_code).decode("utf-8").encode("GBK")









TEST_TEMPLATE_CODE = """\
#模板定义 TEST_DATA 页签1
#模板表头 TEST_DATA 法阵等级 道具ID 道具数量 备注
TEST_DATA = {
	0: (1, 0, "0"),
}


#模板定义 TEST_DATA2 页签2
#模板表头 TEST_DATA2 道具ID 道具数量 消耗1 消耗2
TEST_DATA2 = {
	1: (10, {1: 2})
}
"""

def test2():
	"""
	自定义模板TEST_TEMPLATE_CODE解析输出到文件 test_data
	"""
	mkpyparser.templatemake.templateToFile("./测试导表.xls".decode("utf-8").encode("GBK"), "./test_data.py", TEST_TEMPLATE_CODE)


if __name__ == "__main__":
	test1()
	test2()
