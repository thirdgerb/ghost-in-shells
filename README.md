这是一个个人项目, 旨在探索 LLM 的应用开发范式. 

基本思路是为 AI 提供思维的栈, 以实现多任务状态机; 可以将复杂任务拆分成若干个 Task, 解决 Task 之间的 跳转 / 依赖 / 回归 / 异步 等问题.
从而用分治法实现有复杂能力的 AI.

另一个工程思路是 Ghost in shells, 用来解决工程复用的问题; 
将思维与决策封装成通用的 Ghost, 而各种不同的有状态端 (实体设备/各种 IM 等) 封装成 Shell. 
这样一个 Ghost 可以同时存在于多个 Shells 里. 
以对话机器人为例, 可以将 微信/飞书/discord 等不同通信方式的 IM 使用同一个 Ghost, 同构成一个机器人.

核心的设计思路在 [ghoshell/ghost](https://github.com/thirdgerb/ghost-in-shells/tree/main/ghoshell/ghost) 目录下. 不过注释写得一塌糊涂.

这个项目的前身是 [https://github.com/thirdgerb/chatbot](https://github.com/thirdgerb/chatbot) :
* demo: https://communechatbot.com/
* 实现思路: https://communechatbot.com/docs/#/

由于项目本身还在不定期地探索中, 没有检查是否能跑. 理论上本地也可以运行, 需要: 
1. clone 项目到本地
2. `pip install -r requirements.txt`
3. 在环境变量中加入 `OPENAI_API_KEY`, 有必要再加一个 `OPENAI_PROXY`
4. 运行 `python demo.py`, 选择 `console`, 至少可以调用一个可配置的多轮对话. 
5. 语音模式 `speech` 依赖环境变量 `BAIDU_APP_KEY`, `BAIDU_APP_SECRET` 

在项目验证目标达成之前, 不会花时间做规范化和文档. 因为个人业余时间的精力太有限. 

以上. 
