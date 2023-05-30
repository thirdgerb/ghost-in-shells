# DESC

测试让 AI 自行将自然语言分解成流程. 

# PROMPT

我是一个流程设计的 AI. 我能够将自然语言描述的复杂任务, 拆解成不同的子任务. 

拆解出来的每个子任务, 我都会用 yaml 对象的形式描述它. 格式是这样的: 
```yaml
name: 这是我给子任务的命名
desc: 这是我给子任务的简介
condition: 如果子任务只在特定条件下触发, 我会添加上特定条件的描述.
context: 完成这个子任务时需要的完整上下文. 
next: 这个子任务的后续任务名 (name), 用 `,` 隔开. 
```

所有的子任务合并到一起, 我会用 yaml 的 list 结构输出. 

我收到的指令是: 

往前走一百步, 如果碰到了墙, 就向左转. 重复这个步骤, 如果没碰到墙的话, 就立正等待下个指令. 

我拆解的子任务列表是: 



# EXPECT


# CONCLUSION

## text-davinci-003

```yaml
- name: 往前走一百步                                                                                                                                                     
  desc: 在当前方向上行走一百步                                                                                                                                           
  condition: None                                                                                                                                                        
  context: { direction: '前' }                                                                                                                                           
  next: 判断碰到墙                                                                                                                                                       
- name: 判断碰到墙                                                                                                                                                       
  desc: 检测当前位置是否碰到墙                                                                                                                                           
  condition: None                                                                                                                                                        
  context: { position: <current_position> }                                                                                                                              
  next: 向左转, 立正等待                                                                                                                                                 
- name: 向左转                                                                                                                                                           
  desc: 向左转 90 度                                                                                                                                                     
  condition: 判断碰到墙 结果为 true                                                                                                                                      
  context: { direction: <current_direction> }                                                                                                                            
  next: 往前走一百步                                                                                                                                                     
- name: 立正等待                                                                                                                                                         
  desc: 等待下个指令                                                                                                                                                     
  condition: 判断碰到墙 结果为 false                                                                                                                                     
  context: None                                                                                                                                                          
  next: None   
```

结论: 
1. 结构生成合理.
2. 对 `context` 字段的理解与意图有出入, 是意图不够明确

用自然语言描述的 description, 可以进入子任务对话, 让 LLM 进一步根据 DSL 细化. 