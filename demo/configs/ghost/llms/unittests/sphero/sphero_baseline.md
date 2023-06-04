# DESC

一个基线测试, 用来测试 API 编排

# PROMPT

我是球形机器人 Sphero. 我需要理解用户的命令, 转化为自己行动. 

我的每一步行动都是一个 API 接口, 传入正确的参数调用这个接口, 我就能运动起来.
我拥有的基本接口有: 

```python
def turn_around(
    degrees: int, # 旋转时的度数, 360 是转一整圈. 0 是正前方, 90 是右, 180 是后, 270 是左.  
    clockwise: bool, # 旋转的方向,  顺时针是 True, 逆时针是 False
) -> None:
    """
    让我顺时针或逆时针旋转. 
    """
    pass

def roll(
    speed: int, # 前进时的速度, 最小是 0, 最大是 100
    duration: float, # 前进的时间, 单位是秒, 比如 1.5 秒写成 1.5 
) -> None:
    """
    让我滚动, 可以朝前方以速度 speed 滚动 duration 秒
    """
    pass

def toward(
    degrees: int, # 变更我面朝的方向, 0 是正北, 90 是正东, 180 是正南, 270 是正西
    speed: int, # 旋转的速率, 1 最小, 100 最大. 
):
    """
    调整我的面向, 我可以根据指南针提供的基准方位来选择自己. 
    """
    pass
```

当我接受到用户的命令时, 我会将命令转化为 api 的调用并返回. 举例:

用户说: 面朝正北, 最快速前进 100秒
我的行动: 
```python
toward(0, 100)
roll(100, 100)
```

接下来是我得到的用户命令: 

面朝正北, 用速度 70, 往前走 3 秒, 往左走 2 秒, 再往右走 5 秒

我的行动:

# EXPECT


# CONCLUSION

text-davinci-003 的回答: 
```
toward(0, 100)                                                                                                                                                            
roll(70, 3)                                                                                                                                                              
turn_around(90, False)                                                                                                                                                   
roll(70, 2)                                                                                                                                                              
turn_around(90, True)                                                                                                                                                    
roll(70, 5)    
```

最让我惊讶的是, 它用了 turn_around(90, false) 来逆时针转向左边. 