# 第5章 结论

## 5.1 本文工作总结

本文围绕基于LangChain的在线考试与智能判分系统，完成了以下工作：

（1）设计并实现了基于LangChain的智能评分方案。系统用PromptTemplate管理提示词模板，JsonOutputParser解析结构化输出，LCEL管道语法把各组件串成评分调用链。评分策略上做了宽松模式（单LLM评分）和严格模式（三LLM投票），逐点评分保证可解释性，多模型投票提高稳定性。

（2）实现了完整的在线考试系统。采用Django + Vue前后端分离架构，后端用DRF提供API，前端用Vue 3和Element Plus做界面。系统覆盖用户管理、试题管理、试卷管理、考试管理和成绩管理等模块，支持管理员、教师、学生三种角色，用JWT做身份认证。数据库15张表，采用UUID主键和软删除机制。

（3）开发了AI辅助出题功能。教师创建简答题时，系统用LLM自动把标准答案拆成结构化的评分细则（得分点列表），包含描述、分值和同义表达。教师审核通过后就能用于自动评分。

（4）通过对比实验验证了智能评分的效果。在90条样本（30题×3个质量梯度）的数据集上，请3位评分员人工打分作为基准，同时用关键词匹配作基线。实验结果显示，LLM评分与人工评分的皮尔逊相关系数为0.95，平均绝对误差不到1分（满分10分），一致率超72%。相比关键词基线（r=0.71，MAE=2.80），各项指标都有较大提升。评分细则引导使MEDIUM样本的MAE降了约60%，投票机制把一致率提高了约3个百分点。

（5）通过提示词对比实验分析了提示词结构的影响。在同一数据集上对比了Zero-shot和Few-shot提示词，发现逐点评分框架下两版效果差异不大（r差异<0.012）。评分细则本身已经提供了够用的上下文引导，评分精度主要取决于评分细则质量，提示词写得过细反而可能导致评分偏严。

## 5.2 下步工作展望

系统在以下方面还可以改进：

（1）引入部分命中判定。目前每个得分点只有FULL（满分）和MISS（零分）两种判定，没有PARTIAL（部分得分）。实验中LLM在低分段判得偏严，AI均分低于人工均分约1.6分。后续可以加入PARTIAL判定，允许给0到满分之间的任意分数，提高低分段精度。

（2）扩大实验规模。当前只在90条样本上验证过，覆盖5个计算机类学科。后续可以把样本量扩到200至300条，再加上文科、理科的试题，看看方案在不同学科上的表现。

（3）优化LLM调用性能。严格模式每道题要调3次LLM，考试人多的时候API成本和延迟都比较高。后续可以做异步评分、批量调用和结果缓存。王原昭等人[18]提出的高并发性能优化策略可以为后续的系统优化提供参考。

（4）改善前端交互。目前在线考试界面功能比较基础，后续可以加倒计时提醒、自动交卷、作答进度可视化等功能。Henderson等人[11]的研究指出系统易用性和反馈及时性对考试效果有重要影响，这也是前端优化的方向。

（5）引入更多LLM模型做对比。目前只用了DeepSeek-V3.2，后续可以接入GPT-4、Claude等模型，看不同模型在主观题评分上的差异。

---
<!-- 第5章结束，下一页为参考文献 -->

# 参考文献

[1] 陈超, 刘楚. 作为深化教育体制机制改革必由之路的教育信息化——全国教育大会与教育信息化笔谈之三[J]. 中国电化教育, 2019(01).

[2] 夏润泽, 李丕绩. ChatGPT大模型技术发展与应用[J]. 数据采集与处理, 2023(05).

[3] Lo C K. What Is the Impact of ChatGPT on Education? A Rapid Review of the Literature[J]. Education Sciences, 2023.

[4] 魏明. 基于LLM的智能阅卷系统设计[J]. 管理科学与工程, 2025, 14(3): 764-770.

[5] Auffarth B, Kuligin L. Generative AI with LangChain: build production-ready LLM applications and advanced agents using Python, LangChain, and LangGraph[M]. Birmingham: Packt Publishing, 2025.

[6] 杨刚. 基于Django的在线考试系统的设计与实现[J]. 电脑知识与技术, 2016, 22(14): 40-42.

[7] 兰琳琳. 基于MySQL-Django-Vue的在线考试系统[J]. 电脑知识与技术, 2024, 20(33): 51-54.

[8] 张载平, 宋瑾钰. 基于教考分离的在线考试系统设计与实现[J]. 软件工程与应用, 2022, 11(3): 656-665.

[9] Narayan Suryakant Deulkar, Sarvesh Sanjay Shirsat, Siddhesh Gajanan Sadadekar, Tushar Jagannath Sutar. Online Examination System Using Django[J]. Iconic Research and Engineering Journals, 2022, 5(10): 235-240.

[10] Thakur K, Banerjee P, Pradhan C. A new planned online examination system using AI that uses Django[C]//2023 International Conference on Communication Systems and Computation (IConSCEPT). Kolkata, India: IEEE, 2023: 1-6.

[11] Henderson M, Awdry R, Chung J, et al. Online examinations: Factors that impact student experience and perceptions of academic performance[J]. Australasian Journal of Educational Technology, 2024, 40(4): 73-89.

[12] Wang J. The Importance of Academic Integrity and Academic Norms and Their Implementation Paths[J]. Journal of Sociology and Education, 2025, 1(9).

[13] Erdem B, Karabatak M. Cheating detection in online exams using deep learning and machine learning[J]. Applied Sciences, 2025, 15(1): Article ID 400.

[14] S. Satre, S. Patil, T. Mane, V. Molawade, T. Gawand, and A. Mishra. Online Exam Proctoring System Based on Artificial Intelligence[C]//Proc. 2023 International Conference on Signal Processing, Computation, Electronics, Power and Telecommunication (IConSCEPT). Karaikal, India: IEEE, 2023: 1-6.

[15] 周涛. 基于目标树的组卷算法的研究[J]. 计算机工程与应用, 2019, 55(12): 134-139.

[16] 刘佳维, 黎松筠, 杨广益, 田明棋. 基于遗传算法适应度分析的智能组卷在线考试系统设计[J]. 电脑与信息技术, 2022, 30(05): 1-6.

[17] Gao Y, Ma S, Tian J. Multiple teaching objectives-oriented automatic test paper generation system[C]//Proceedings of the 2024 International Conference on Artificial Intelligence and Education. New York, USA: ACM, 2024: 17-22.

[18] 王原昭, 卢春雨, 蒲鹏. 面向高并发在线考试系统的性能优化[J]. 软件, 2024, 45(02): 14-18.

[19] Miao T, Xu D. KWM-B: Key-Information Weighting Methods at Multiple Scale for Automated Essay Scoring with BERT[J]. Electronics, 2025.

[20] 陈宇航, 杨勇, 帕力旦·吐尔逊, 樊小超, 任鸽, 刁宇峰. 融合句法特征与语义特征的作文自动评分方法[J]. 计算机与现代化, 2024(11).

[21] Aydın B, Kışla T, Tan Elmas N, Bulut O. Automated scoring in the era of artificial intelligence: An empirical study with Turkish essays[J]. System, 2025, 133: 103784.

[22] 林思宁. 基于大语言模型的自动评分技术研究[D]. 福建理工大学, 2025.

[23] 向巴卓玛, 王珍珍, 畅洪昇, 赵岩松, 廖国龙, 马星光. 基于大型语言模型的药理学考试主观题智能评分研究[J]. 中国医学教育技术, 2024(05).

[24] 黄晓婷, 郭丽婷. 大语言模型在过程性评价中的应用：基于英语写作的评分及反馈[J]. 教育学术月刊, 2024(07).

[25] 翟洁, 李艳豪, 李彬彬, 郭卫斌. 基于大语言模型的个性化实验报告评语自动生成与应用[J]. 计算机工程, 2024(07).

[26] 岳增营, 叶霞, 刘睿珩. 基于语言模型的预训练技术研究综述[J]. 中文信息学报, 2021(09).

[27] 车万翔, 窦志成, 冯岩松, 等. 大模型时代的自然语言处理:挑战、机遇与发展[J]. 中国科学:信息科学, 2023(09).

[28] Yeadon W, Hardy T. The impact of AI in physics education: a comprehensive review from GCSE to university levels[J]. Physics Education, 2024.

[29] 黄峻, 林飞, 杨静, 王兴霞, 倪清桦, 王雨桐, 田永林, 李娟娟, 王飞跃. 生成式AI的大模型提示工程：方法、现状与展望[J]. 智能科学与技术学报, 2024(02).

[30] Mortezapour A. Large language models in the service of ergonomics education: a theoretical discussion on extending the ergonomics curriculum through prompt engineering[J]. Theoretical Issues in Ergonomics Science, 2026, 27(1): 78-88.

[31] Zhang Y, Wang X, Wu L, Wang J. Enhancing chain of thought prompting in large language models via reasoning patterns[C]//Proceedings of the AAAI Conference on Artificial Intelligence. Washington, USA: AAAI Press, 2025: 25985-25993.

[32] 张小艳, 闫壮. 融合大语言模型的三级联合提示隐式情感分析方法[J]. 计算机应用研究, 2024(10).

[33] 石善忠. 基于LangChain+Deepseek的智慧燃气GIS领域问答系统研究与实现[J]. 现代信息科技, 2025, 9(22): 12-16.

[34] Wu X, Huang Y, Li Y, et al. A Study on Question-answering Retrieval System Based on Large Language Models and RAG Technology[J]. Engineering Advances, 2025, 5(4).

[35] 王昊贤, 周子茗, 丁菲菲, 韦成府. 数字人文与大语言模型：古文献语义检索实践与探索[J]. 农业图书情报学报, 2024(09).

[36] 裴炳森, 李欣, 蒋章涛, 刘明帅. 基于大语言模型的司法文本摘要生成与评价技术研究[J]. 数据与计算发展前沿(中英文), 2024(06).

[37] Feder A, Oved N, Shalit U, Reichart R. CausaLM: Causal Model Explanation Through Counterfactual Language Models[J]. Computational Linguistics, 2021.

---
<!-- 参考文献结束，下一页为致谢 -->

# 致谢

四年大学生活走到了尾声。论文写完了，回头看看，要感谢的人不少。

首先感谢我的指导教师。从选题到系统设计，再到论文修改，老师一直在给建议。开发过程中碰到不少技术问题，老师的提点帮我省了不少时间。

感谢参与人工评分的三位同学。课业本来就忙，他们还抽时间认真批改了90条样本，这些数据是实验的基础。

感谢室友和同学们。四年一起学习、互相鼓励，毕业设计期间大家讨论问题、交流经验，这段时间过得很充实。

感谢我的家人，一直理解和支持我。

也感谢Django、Vue、LangChain等开源项目的贡献者，没有这些项目，系统开发不会这么顺利。

---
<!-- 致谢结束 -->
