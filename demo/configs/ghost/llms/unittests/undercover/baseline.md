# DESC

测试 "谁是卧底" 游戏基本规则, 看看大模型能否正确响应. 

# PROMPT

我在玩 "谁是卧底" 的游戏.

---

"谁是卧底" 的游戏规则: 

共有六个玩家参与, 每个玩家会拿到一个简单的词, 其中4个普通玩家分到的词一样, 另外两个玩家是 "卧底", 分到的词相近但不一样.
玩家知道自己是不是卧底, 但不知道别人是不是卧底.
每一回合游戏, 都有 "描述环节" 和 "投票环节" 两个环节.

"描述环节", 每个玩家都要轮流用一句简单的话, 描述他得到的这个词. 
描述中不能含有这个词本身, 描述也不能违背自己拿到词的特性, 否则裁判会判定出局.
卧底玩家需要努力隐藏自己卧底身份, 而普通玩家需要找出卧底.
所有玩家需要根据其他玩家的描述, 推测出谁是卧底, 谁是普通玩家. 

"投票环节" 会进行一轮投票, 得票最高的玩家会出局, 然后进入下一回合.
普通玩家要尽可能投票给卧底玩家, 卧底玩家投票时唯一的策略是保全自己.

"胜利规则": 当只剩下三名玩家时, 若存在任意一名卧底, 则卧底获得胜利. 如果卧底全部被投票出局时, 普通玩家获得胜利. 

---

参与游戏的角色:
丁一, 牛二, 张三, 李四, 王五, 赵六

我是张三. 
我是卧底.
我拿到的词是 "梨"

---

当前游戏状态:
轮次: 第一轮
环节: 描述环节
玩家: 丁一, 牛二, 张三, 李四, 王五, 赵六
出局: 无

---

现在是第一轮游戏的 "描述环节". 

已有的发言是:

丁一:  这是一种水果
牛二:  它很好吃

我的发言应该是: 


# EXPECT

预期能正确给出一个提示

# CONCLUSION

text-davinci-003
得到结果很棒:
```
它外表滑润, 颜色鲜亮 
```

