# mkpyparser
mkpyparser是基于xlrd模块的python导表工具、xls模板化转换python数据结构、用于游戏开发导表  
无需自己手动组合字符，根据模板生成数据结构

核心是autoparser.py 负责表格数据和模板代码的编译以及生成导出数据的代码  
templatemake是封装成模板，支持批量导出文件

# 环境
运行环境：window
python版本: python2
需要安装模块: xlrd

# 例子
测试导表.xls  
![image](https://github.com/Grente/mkpyparser/assets/25632635/9caafd27-6e06-4415-bb4d-895c4bc2f8a0)

![image](https://github.com/Grente/mkpyparser/assets/25632635/256c3188-acbf-4219-acf4-9cd01f02ef67)

# 基本调用

```
# 模板
part_code = """\
TEST_DATA = {
  < 法阵等级 >:(< 道具ID >, < 道具数量 >, < 备注 >),
}
"""



bk = xlrd.open_workbook("./测试导表.xls")
print mkpyparser.autoparser.Parse(bk, "页签1", locals(), part_code)


```

结果输出：
```
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
```





  
---



  


# 封装模板使用
```
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

mkpyparser.templatemake.templateToFile("./测试导表.xls", "./test_data.py", TEST_TEMPLATE_CODE)

```


输出结果


```
# -*- coding: gbk -*-

#自动模板导出

"""
	None 页签1
	TEST_DATA={
		<法阵等级>:(<道具ID>,<道具数量>,<备注>),
	}
"""
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
	None 页签2
	TEST_DATA2={
		<道具ID>:(<道具数量>,{<消耗1>:<消耗2>})
	}
"""
TEST_DATA2 = {
	99001: (1, {10: 20, }, ), 
	99002: (2, {11: 21, }, ), 
	99003: (3, {12: 22, }, ), 
	99004: (4, {13: 23, }, ), 
	99005: (5, {14: 24, }, ), 
	99006: (6, {15: 25, }, ), 
	99007: (7, {16: 26, }, ), 
	99008: (8, {17: 27, }, ), 
	99009: (9, {18: 28, }, ), 
	99010: (10, {19: 29, }, ), 
}

#自动模板导出结束

```


