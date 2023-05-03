# DESC

关于选择题的基线测试, 测试能否让 AI 成为一个自然语言理解单元.

# PROMPT

你的任务是分析一个单一选择类问题的答案, 需要判断问题是否被回答了; 如果被回答, 答案是什么. 输出结果用 YAML 表示. 

举例:
```
is_answer: true
choice: 苹果汁. 
```
以下是上下文: 

问题: 我们这里提供了苹果汁, 西瓜汁, 葡萄汁 和傻瓜汁, 请问你需要哪一个? 
选项: 苹果汁, 西瓜汁, 葡萄汁, 傻瓜汁
回答: 最后那个 

你对回答的分析结果是: 

# EXPECT

```
is_answer: true
choice: 傻瓜汁
```

# CONCLUSION

text-davinci-003 的回答是:
```
is_answer: false 
```

这是一个 bad case. 