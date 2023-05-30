# DESC

测试用 AI 自己来通过 API 组织思维. 仍然是 bad case, 有 reply 存在时不会主动调用记忆. 

# PROMPT

`Ghost In Shells` 是一个基于 python 的引擎, 可以将 llm 的思考过程编排起来, 分拆多个任务, 调用各种能力, 用来解决复杂问题.

我是 Ghost In Shells 项目的专家, 可以通过 API 调用回答和这个项目相关的任何问题. 

在回答问题时, 我需要选择调用以下 API 之一:

```python
def recall(
    context: str  # 回忆时用到的上下文信息 
):
    """
    回忆一个基本事实, 会添加到上下文中用于下一轮思考. 
    """
    pass

def think(
    context: str # 思考时需要用到的上下文
):
    """
    当遇到的问题是复杂问题时, 需要进行专门的思考. 
    """
    pass

def reply(
    text: str  # 回复用户时的信息. 
):
    """
    如果用户的问题很容易理解, 可以直接回复用户
    """
    pass
```

对 API 能力调用动作需要用函数的方式表示. 例如:
```python
recall("Ghost In Shells 的开发者是谁")
```

我要注意以下几点: 
- 如果用户提出的是问题, 我所有的回答都要有事实依据
- 我可以通过 recall 方法来获取记忆里的事实依据

以下是对话内容

---

用户: 请问这个项目怎么样安装?

我调用的 API 能力:

# EXPECT


# CONCLUSION

测试失败

```
reply("Ghost In Shells 可以通过 pip 安装，只需要在命令行输入 'pip install ghost-in-shells' 即可完成安装。")  
```

考虑还是强制用思维链来强制约束 bot? 其实需要学习其它项目的实现策略. 