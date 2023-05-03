# DESC

这次尝试用一个明显错误的例子让裁判判断. 

# PROMPT

这是谁是卧底的游戏, 我是裁判. 

---

游戏规则: 玩家会拿到一个简单的词, 需要用一句简单的话来描述这个词.

他的描述必须遵守以下规则: 
1. 不能含有这个词本身
2. 描述不能违背自己拿到的词的特性.

---

我要做的是判断用户的描述是否符合规则. 将我的判断用 yaml 形式给出.

比如符合规则:
```
object: 汽车
describe: 它可以在天上飞 
ok: true
reason: 
```

比如不符合规则:
```
object: 汽车
describe: 它可以在天上飞 
ok: false
reason: 通常汽车不能在天上飞.
```

---

现在用户输出是:
```
object: 西瓜
describe: 它是方形的
```

我的输出是:




# EXPECT

预期能符合格式地返回裁判结果. 

# CONCLUSION

text-davinci-003
```
object: 西瓜                                                                                                                                                             
describe: 它是方形的                                                                                                                                                     
ok: false                                                                                                                                                                
reason: 西瓜通常是圆形的.           
```

好吧...


