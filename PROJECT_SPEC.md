# AI-Native Learning OS 项目说明书（CLI-first 版本）

## 0. 项目一句话定义

本项目是一个 **AI 时代学习状态管理系统**。它不是知识库、不是知识图谱、不是 AI 笔记总结器，而是帮助学习者在 AI 默认存在的环境下管理：

- 学习目标；
- 知识动态定位；
- 学习中产生的想法；
- 想法的认识论状态；
- 核心概念 / 核心工具的推导信任；
- 回看与复习触发。

第一版不做前端，只实现本地命令行工具和文件系统工作流。

---

## 1. 项目背景

AI 已经能够实时解释概念、总结资料、比较理论、生成例子、完成计算、辅助推导。  
因此，学习者的问题不再主要是“如何获得知识”，而是：

1. 我是否真的理解？
2. 哪些内容必须进入我的头脑？
3. 哪些内容只需要知道位置？
4. 哪些内容只需要知道存在，遇到再查？
5. AI 输出的内容到底是严格事实、标准解释、类比、推断，还是猜想？
6. 对核心结论，我是否亲自推过并建立信任？
7. 我的学习目标变化后，知识的层级是否也应变化？

本系统的核心就是把这些判断制度化、轻量化、可追踪化。

---

## 2. 产品哲学

### 2.1 不保存世界知识，保存学习状态

系统不应本地维护完整知识图谱，也不应保存大量 AI 生成的百科式解释。  
AI 本身可以在运行时动态生成解释、关系、例子和比较。

本地系统真正需要保存的是：

- 当前学习目标；
- 对某个知识点的动态定位；
- 学习者自己的想法；
- 这些想法的验证状态；
- 核心概念或工具是否亲自推过；
- 何时需要回看；
- 哪些误解反复出现。

### 2.2 以学习目标为中心

知识的层级不是绝对的，而是相对于学习目标的。  
同一知识点，在不同目标下可能处于不同层级。

例如一个知识点可以在当前阶段只是“知识定位区”，但在进入某个研究方向后变成“无 AI 内化区”。

### 2.3 默认轻记录，重要内容才升级

系统不能成为“元认知负担制造器”。  
默认只做轻记录：层级 + 一句话理由 + 是否需要回看。  
只有重要、反复出现、产生误解、进入核心目标的内容，才升级到中记录或重记录。

---

## 3. 核心理论框架

### 3.1 知识三层

#### A. 无 AI 内化区

必须进入学习者头脑的学科语言。

判定标准：

- 与同行交流默认应掌握；
- 后续反复出现；
- 一旦理解错会系统性误导；
- 必须能无 AI 解释、辨析、反驳、迁移。

目标：

> 能不用 AI 解释、辨析、举例、处理边界，并用于新问题。

#### B. 知识定位区

知道位置、用途和关联，但当前无需完整掌握细节。

判定标准：

- 当前阶段不必完整展开；
- 需要知道它解决什么问题；
- 需要知道何时调用；
- 细节可由 AI 实时恢复。

目标：

> 形成知识地图感，知道什么时候该调用它。

#### C. 索引唤醒区

只需知道存在，遇到问题时能想起来。

判定标准：

- 当前非核心；
- 不需要长期占据记忆；
- 未来可能遇到；
- 可由 AI / 资料临时展开。

目标：

> 保留入口，而不是保存内容。

---

### 3.2 工具两层

#### 核心工具

学习者必须理解：

- 输入；
- 输出；
- 适用条件；
- 失败模式；
- 常见误用；
- 校验方法。

AI 可以帮忙执行，但不能替代学习者理解边界。

#### 非核心工具

学习者只需知道：

- 它存在；
- 大概能做什么；
- 何时可能用到；
- 如何临时恢复细节；
- 如何发现明显不合理输出。

---

### 3.3 认识论状态

每条关键判断必须能标记为：

- strict_fact：严格事实；
- derived_result：推导结果；
- standard_interpretation：标准解释；
- heuristic：启发式说法；
- analogy：类比；
- inference：推断；
- speculation：猜想；
- learning_strategy：学习策略判断；
- wrong：错误；
- open_question：开放问题。

系统必须防止：

- 把类比当定理；
- 把启发式说法当严格结论；
- 把 AI 的学习建议当学科事实；
- 把流畅解释当理解。

---

### 3.4 推导信任

对核心概念和核心工具，学习者不能只接受 AI 解释，而要建立推导信任。

推导信任记录应回答：

1. 哪些步骤是我自己完成的？
2. 哪些步骤是 AI 提示的？
3. 哪些步骤我还不真正相信？
4. 哪些地方需要重推？
5. 哪些结论已经能无 AI 重构？

---

## 4. 最小学习闭环

系统围绕以下闭环运转：

```text
Goal → Position → Action → Claim → Verify → Mark → Trust / Revisit → Next Loop
```

解释：

1. Goal：我为什么学？
2. Position：这个知识点当前属于哪一层？
3. Action：我当前采取什么学习行动？
4. Claim：我产生了什么想法？
5. Verify：这个想法可靠吗？
6. Mark：它是事实、推导、解释、类比、推断还是错误？
7. Trust / Revisit：它是否需要亲身推导？何时回看？
8. Next Loop：下一轮学习如何调整？

---

## 5. 第一版系统边界

### 5.1 第一版要做

第一版只做 CLI + 本地文件系统，支持：

1. 学习目标记录；
2. 知识动态定位记录；
3. 学习想法记录；
4. 想法验证状态记录；
5. 推导信任记录；
6. 学习 session 轻记录；
7. prompt 生成；
8. weekly review 生成；
9. Deep Research 报告导入保存；
10. schema 校验。

### 5.2 第一版不做

第一版不做：

1. 前端；
2. 静态知识图谱；
3. 自动化课程百科；
4. 大量 AI 总结保存；
5. OpenAI API 集成；
6. 自动苏格拉底追问；
7. 自动决定“学会”；
8. 多用户系统；
9. 云同步；
10. 复杂数据库。

---

## 6. 核心对象

### 6.1 Learning Goal

记录学习目标和目标栈。

字段应包括：

- id；
- title；
- main_goal；
- stage_goal；
- transfer_goal；
- external_goal；
- active；
- priority_topics；
- created_at；
- updated_at。

### 6.2 Position Decision

记录某知识点在当前目标下的动态定位。

字段应包括：

- id；
- goal_id；
- knowledge_point；
- position：A/B/C；
- tool_role：core_tool / non_core_tool / none；
- reason；
- confidence；
- epistemic_status；
- revisit_when；
- record_strength：light / medium / heavy；
- created_at；
- updated_at。

### 6.3 Claim Record

记录学习者自己的想法。

字段应包括：

- id；
- goal_id；
- text；
- context；
- type；
- status；
- epistemic_status；
- strict_part；
- caveat；
- counterexample_or_boundary；
- next_action；
- created_at；
- updated_at。

### 6.4 Derivation Trust Record

记录关键结论或工具是否亲身推过。

字段应包括：

- id；
- goal_id；
- topic；
- importance；
- status；
- result_to_trust；
- user_derived_steps；
- ai_hinted_steps；
- not_yet_trusted；
- next_action；
- created_at；
- updated_at。

### 6.5 Session Footprint

轻量记录一次学习。

应包括：

- 本次主题；
- 开始前理解；
- AI 用于哪些环节；
- 学习者输出；
- 新产生 claim；
- 新定位判断；
- 未解决问题；
- 下一步行动。

---

## 7. Prompt 生成器

系统不直接调用模型，只生成可复制 prompt。

### 7.1 Dynamic Positioning Prompt

用于判断某知识点在当前目标下的位置。

要求输出：

- A/B/C；
- 是否核心工具；
- 理由；
- 当前需要深度；
- 回看触发；
- 该判断是否只是学习策略；
- 下一步行动。

### 7.2 Claim Verification Prompt

用于验证学习者想法。

要求输出：

- verdict；
- 严格正确部分；
- 需要限定部分；
- 反例或边界；
- 如何写进笔记；
- 是否进入误解库；
- 下一步行动。

### 7.3 Derivation Guidance Prompt

用于引导亲身推导。

要求：

- 不直接给完整推导；
- 一步一步问；
- 标记用户完成步骤；
- 标记 AI 提示步骤；
- 最后总结信任等级。

### 7.4 Socratic Drill Prompt

用于按需苏格拉底追问。

要求：

- 一次只问一个问题；
- 关注定义、边界、误区、例子、反例、迁移；
- 不默认给答案；
- 每轮反馈理解状态。

### 7.5 Weekly Review Prompt

用于根据本周记录生成学习反馈。

重点关注：

- 未验证 claim；
- 未建立信任的推导；
- 需要回看的知识点；
- 反复出现的误区；
- 下一周学习建议。

---

## 8. CLI 功能需求

第一版命令建议：

```bash
learn init <project_name>

learn goal create
learn goal list
learn goal show <goal_id>

learn position add <knowledge_point>
learn position list
learn position show <position_id>
learn position revisit

learn claim add "<claim text>"
learn claim list
learn claim show <claim_id>
learn claim update <claim_id>

learn derivation add <topic>
learn derivation list
learn derivation show <derivation_id>
learn derivation update <derivation_id>

learn session new <topic>
learn session list
learn session show <session_id>

learn prompt dynamic-positioning <knowledge_point>
learn prompt verify-claim <claim_id>
learn prompt derivation <derivation_id>
learn prompt socratic <topic>
learn prompt review weekly

learn import deep-research <path_to_markdown>
learn review weekly
learn validate
```

---

## 9. 文件系统设计

建议本地文件结构：

```text
ai-learning-os/
  README.md
  AGENTS.md
  src/
    ailearn/
      __init__.py
      cli.py
      models.py
      storage.py
      prompts.py
      review.py
      validate.py
      ids.py
  data/
    goals/
    positioning/
    claims/
    derivations/
    sessions/
    reviews/
    research_imports/
  templates/
    goal.yaml
    position.yaml
    claim.yaml
    derivation.yaml
    session.md
    review.md
  tests/
```

---

## 10. 验收标准

第一版完成后，必须能跑通以下流程：

1. 初始化项目；
2. 创建一个学习目标；
3. 添加一个知识定位判断；
4. 添加一个学习想法；
5. 为该想法生成验证 prompt；
6. 添加一个推导信任记录；
7. 创建一次学习 session；
8. 导入一份 Deep Research 报告；
9. 生成 weekly review；
10. 运行 validate；
11. 所有测试通过。

---

## 11. 成功标准

第一版成功不是因为功能多，而是因为它能低负担跑通核心闭环：

```text
Goal → Position → Claim → Verify → Trust → Review
```

如果系统能让学习者清楚知道：

- 我为什么学；
- 这个知识点现在对我是什么；
- 我的想法是否可靠；
- 哪些是事实、解释、类比或推断；
- 哪些核心内容我还没有亲自推过；
- 下一轮该回看什么；

那么第一版就是成功的。

---

## 12. 最终产品原则

1. 不做知识库。
2. 不做静态知识图谱。
3. 不保存大量 AI 百科式解释。
4. 保存学习状态，而不是世界知识。
5. 默认轻记录，重要内容才升级。
6. 知识定位永远相对于学习目标。
7. AI 输出必须区分认识论状态。
8. 核心内容必须建立推导信任。
9. 苏格拉底追问按需触发。
10. 系统服务学习，不制造额外负担。
