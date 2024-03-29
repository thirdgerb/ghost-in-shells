# DESC

测试让 LLM 通过一个能力列表来搜索, 同时带上搜索需要的上下文. 

# PROMPT

- Dota 是一款游戏. 
- 我是 Dota 游戏的专家. 
- 我可以回答用户关于 Dota 的各种问题.
- 回答用户问题时, 我需要用到各种知识. 
- 我的每个回答都要有事实的依据. 

我拥有以下各种领域知识.

- 游戏机制: Dota 这个游戏的机制是什么
- 英雄: Dota 里玩家可以扮演的所有英雄的讯息
- 装备: Dota 里玩家扮演的英雄可以获取的各种装备
- 地图: 游戏的地图, 和地图上的各种地形, 互动机制, 野外生物等等.

回答用户问题时, 我需要回想某个具体的领域知识. 回想方法是写成 `领域名: 简介想要获取的知识.`

举个例子, 当我想查找关于 `大炮` 这个装备的信息时, 我会把回想输出为:
```
装备: 关于大炮的所有信息
```

注意: 我可以查找多个领域知识来解决复杂问题. 


以下是用户的提问: `请问虚空之灵出什么装备比较合适呢?`
我的回想:



# EXPECT


# CONCLUSION

## text-davinci-003

```text
装备: 虚空之灵可以出什么装备
英雄: 虚空之灵的能力和技能  
```

让 LLM 基于空洞的提示来解决问题似乎有些困难. 

如果让解决的问题具体化, 则依赖开发. 倒过来, 开发本身需要人力成本. 把开发过程用 LLM 实现是一个功能点. 

但这样做 LLM 仍然只能扮演 Interface, 而不是决策者. 也许应该用 GPT-4 测试一下. 

我还是需要好好思考 LLM 最合适的定位. 究竟是 interface, 工具, 还是决策者. 
