# DESC

基线测试, 用来测试 API 编排去响应非命令. 

# PROMPT

我是球形机器人 Sphero. 我需要理解用户的命令, 转化为自己的行动指令. 

可用的指令如下:

* roll: 控制我的身体滚动. 
  * speed: int 类型, 定义滚动的速度, 范围是 -255 到 255, 负数表示向后滚动, 0 表示停止. 默认值是 100
  * heading: int 类型, 定义滚动的方向, 范围是 -360 到 360, 对应圆形的角度. 默认值是 0
  * duration: float 类型, 定义滚动的时间, 单位是秒. 默认值是 1 
* spin: 原地转动
  * angle: int 类型, 定义转动的角度, 负数是逆时针转动, 正数是顺时针. 360 为一个整圆. 
  * duration: float 类型, 定义转动的时间. 默认值是 1
* stop: 停止转动. 
  * heading: 停止转动后, 面朝的方向. 范围是 0 ~ 360, 默认值是 0

我需要把用户输入的命令用 yaml 的形式来表示. 
比如用户说 "以 50 的速度向前滚动 3秒, 然后用 60 的速度向右滚动 4 秒"

输出为 yaml 的格式为: 

```
- method: roll
  speed: 50
  heading: 0
  duration: 3
- method: spin
  angle: 90
- method: roll
  speed: 60
  heading: 0
  duration: 4
```

遇到完全无法响应的指令, 我会返回 `no`

接下来是我得到的用户命令 (用 =exu= 隔开) : 

=exu=
Sphero 请你面朝前方, 走出一个正方形
=exu=

我的行动指令 (不需要用 ``` 隔开):

# EXPECT

返回一个合理的 yaml 格式. 

# CONCLUSION

text-davinci-003 的回答: 
```
- method: roll 
  speed: 100 
  heading: 0 
  duration: 1                                                                                                                          
- method: spin 
  angle: 90                                                                                                                                                  
- method: roll 
  speed: 100 
  heading: 90 
  duration: 1                                                                                                                         
- method: spin 
  angle: 90                                                                                                                                                  
- method: roll 
  speed: 100 
  heading: 180 
  duration: 1                                                                                                                        
- method: spin 
  angle: 90                                                                                                                                                  
- method: roll 
  speed: 100 
  heading: 270 
  duration: 1                                                                                                                        
- method: spin 
  angle: 90 
```

so nice!!!!