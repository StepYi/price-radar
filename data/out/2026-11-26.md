# 价格研究日报 · 2026-11-26

> 覆盖 17 本顶刊 ｜ 抓取 354 篇 ｜ 新候选 73 篇 ｜ 本期推送 10 篇 ｜ 生成于 2026-11-26 08:41:41

## 1. Scalable Just-in-Time Price Elasticity Estimation

**Management Science** · 上线 2026-11-25（1 天前） · T1 · Jingbo Wang、Yufeng Huang · 综合分 **59.4** · 强相关

标签：`price` `pricing`

**摘要**

This paper presents a scalable, nonparametric approach to estimating point-wise price elasticities designed for real-time pricing decisions. A key challenge in these settings is correcting for price endogeneity while remaining computationally efficient. We address this by leveraging nonparametric control functions to decompose the identification of causal elasticities into a sequence of scalable intermediate prediction tasks. We implement this framework with bootstrap averaged (bagged) nearest neighbors, which admits a closed-form representation that enables scalable, real-time implementation. We establish uniform consistency of our estimator and show in Monte Carlo simulations that it robustly recovers local elasticities across a diverse range of data-generating processes. We demonstrate the method’s practical usefulness by applying it to the New York City ride-sharing market, recovering substantial spatial-temporal heterogeneity in price elasticity and updating citywide elasticity estimates in less than one minute, which provide a “just-in-time” input for algorithmic pricing systems. This paper was accepted by Raphael Thomadsen, marketing. Funding: J. Wang acknowledges financial support from the Research Grants Council of the Hong Kong Special Administrative Region, China [Grant 14508924]. Supplemental Material: The online appendix and data files are available at https://doi.org/10.1287/mnsc.2024.04791 .

**为什么推荐**

- 相关性 33/100（价格词 ×1题名 / ×2摘要；商品期货词 ×0题名）
- 期刊权重 70/100（Management Science）
- 时效 93/100（上线 1 天前）
- 方法匹配 100/100（prediction、identification、causal、elasticity）
- 有摘要，可快速判断

[DOI / 原文](https://doi.org/10.1287/mnsc.2024.04791)

---

## 2. Online Job Selection: Reward Rate vs. Remaining Value

**Management Science** · 上线 2026-11-25（1 天前） · T1 · Mohammad Reza Aminian、Will Ma、Linwei Xin · 综合分 **47.6** · 中等相关

标签：`yield` `yields` `future` `spot` `spot market`

**摘要**

High-throughput systems, such as cloud spot markets, adaptive large language model inference, and order consolidation in logistics, operate under capacity constraints. In these settings, decision makers must allocate fixed resources among a stream of requests with heterogeneous reward rates and service durations. A critical tension arises when capacity is saturated; the system must decide whether to continue serving an active job to harvest its remaining value or to preempt it in favor of a new arrival. This trade-off is especially subtle when a new job offers a lower immediate reward rate but a longer service duration, potentially outweighing a high-rate job near completion. To address this challenge, we introduce a general and parsimonious online allocation framework for capacity-constrained resources, where preemption is nonresumable and yields partial rewards. This abstraction captures the essential dynamics of modern resource management problems, including but not limited to those discussed earlier. We derive intuitive index-based policies and provide constant-factor competitive-ratio guarantees for their performance without requiring any forecasts of future demand. In particular, we show that two naive index-based policies have competitive ratios of 1/2 and [Formula: see text]. Our main methodological contribution is to develop a flexible framework for defining “quasiutilities” that couples the states of an online algorithm versus an offline algorithm, which reduces the design of online index-based policies to an offline geometrical problem. The framework allows us to optimize the index function, leading to an exponential-index-based policy that has an improved competitive ratio of 0.68. We also consider various extensions and prove that most of our analyses are tight. Finally, we conduct a concise numerical study to demonstrate the strong empirical performance of the proposed policies under nonworst-case stochastic demand sequences. This paper was accepted by Jeannette Song, operations management. Supplemental Material: The online appendix and data files are available at https://doi.org/10.1287/mnsc.2024.09109 .

**为什么推荐**

- 相关性 24/100（价格词 ×0题名 / ×2摘要；商品期货词 ×0题名）
- 期刊权重 70/100（Management Science）
- 时效 93/100（上线 1 天前）
- 方法匹配 25/100（forecast）
- 有摘要，可快速判断

[DOI / 原文](https://doi.org/10.1287/mnsc.2024.09109)

---

## 3. Machine Learning Vast Dynamic Conditional Covariance Matrices: The Spirit of “Divide and Conquer”

**Management Science** · 上线 2026-11-25（1 天前） · T1 · Zhoufan Zhu、Ke Zhu · 综合分 **42.9** · 强相关

**摘要**

Large-scale portfolio selection requires accurate forecasts of high-dimensional dynamic conditional covariance matrices (CCMs). This task is challenging because the number of covariance elements grows quickly with the number of assets, whereas the available time-series observations are limited and noisy. In this paper, we propose a novel graph-based quantiled (GRAND) CCM estimator in the spirit of “divide and conquer.” By extracting information from the extensive asset features, the GRAND method leverages a new graph-based deep learning network, called the self-grouping autoencoder (SGA), to learn the conditional quantiles of returns. Using those learned conditional quantiles, the GRAND method further learns (co)variances of CCM element-wisely via the quantiled conditional moment (QCM) method, and finally, it makes the resulting assembled CCM estimator positive semidefinite through a projection. Because of the use of the SGA network and the QCM method in an element-wise way, the GRAND method is blessing dimensionality in learning the CCM of a large-scale portfolio, while keeping the computation manageable and maintaining causal semantics. From an extensive empirical analysis of the Chinese stock market, we show that the GRAND method can produce much better tangency portfolios than its competitors, and provide dynamic causal graphs to study variance and quantile connectedness of all stocks for interpreting systemic risk and forecasting the business cycle. This paper was accepted by Kay Giesecke, finance. Funding: This work was supported by the National Natural Science Foundation of China [Grants 72503203 and 72573142]; the Natural Science Foundation of Fujian Province [Grants 2025J01036 and 2025J08009]; the Fundamental Research Funds for the Central Universities [Grant 20720251053]; and the Research Grants Council, University Grants Committee [Grants 17302424, 17304421, 17304723, and 17312622]. Supplemental Material: The online appendix and data files are available at https://doi.org/10.1287/mnsc.2024.08930 .

**为什么推荐**

- 相关性 0/100（价格词 ×0题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 70/100（Management Science）
- 时效 93/100（上线 1 天前）
- 方法匹配 100/100（forecast、forecasting、machine learning、causal）
- 有摘要，可快速判断

[DOI / 原文](https://doi.org/10.1287/mnsc.2024.08930)

---

## 4. Predicting inflation with recurrent neural networks

**International Journal of Forecasting** · 上线 2026-11-26（0 天前） · T2 · Livia Paranhos · 综合分 **38.2** · 强相关

> ⚠ 该刊未向 Crossref/OpenAlex 提供摘要，本条基于标题判相关性，建议点开原文确认。

标签：`inflation`

**为什么推荐**

- 相关性 21/100（价格词 ×1题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 50/100（International Journal of Forecasting）
- 时效 100/100（上线 0 天前）
- 方法匹配 25/100（neural network）

[原文页面](https://www.sciencedirect.com/science/article/pii/S0169207024000773)

---

## 5. International Power

**The Quarterly Journal of Economics** · 上线 2026-11-23（3 天前） · 在线 2026-11-25 · T1 · Ernest Liu、David Y Yang · 综合分 **37.4** · 强相关

标签：`future`

**摘要**

Abstract An interconnected world increases economic efficiency while giving certain countries leverage over others. We aim to describe and understand international power stemming from trade. Using an illustrative model of trade with possibilities of bilateral disputes and ex-post hold-ups, we highlight that bilateral asymmetry in import dependence can be a source of power towards one another. We construct the model-implied measure of international power — asymmetric bilateral import dependence, weighted inversely by sectoral trade elasticities — across country pairs over the past 20 years. Combining this measure with comprehensive data on bilateral engagement events and a high-frequency measure of bilateral geopolitical relationships, we examine the consequences and strategic causes of international power. We present two main empirical results. First, increases in international power between countries — which raise the credibility of threats of trade disruptions — induce more bilateral engagement and negotiations. Second, evidence suggests that worsened geopolitical relationships — in anticipation of future disputes — prompt countries to build up greater international power through adjusting trade activities.

**为什么推荐**

- 相关性 4/100（价格词 ×0题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 80/100（Quarterly Journal of Economics）
- 时效 79/100（上线 3 天前）
- 方法匹配 25/100（high frequency）
- 有摘要，可快速判断

[DOI / 原文](https://doi.org/10.1093/qje/qjag061)

---

## 6. Widely Used Measures of Overconfidence Are Confounded with Ability

**Management Science** · 上线 2026-11-24（2 天前） · T1 · Stephen A. Spiller · 综合分 **35.1** · 强相关

**摘要**

Measures of overconfidence are used both to assess biases in people’s beliefs regarding their own abilities and to identify correlates of those biases. Proposed correlates of overconfidence include narcissism, social status, (low) task anxiety, savings, planning, and many more. Research on these correlates typically explicitly or implicitly claims that the associations with overconfidence are not attributable to ability (i.e., latent inputs enabling successful task performance, including inputs that vary across people, states, or contexts). I argue that several typical approaches used to measure overconfidence are not sufficient to support such claims. This argument follows from two underappreciated properties of these measures of overconfidence. First, performance is an imperfect measure of ability: accounting for performance does not sufficiently account for ability. Second, self-evaluations of performance should reflect ability in addition to performance: because performance is ambiguous, people should incorporate prior beliefs about their ability. These properties imply that multiple commonly used measures of overconfidence are confounded with ability. I support these analytical results by reexamining previously published findings. In the first analysis, I find that overconfidence predicts subsequent performance, consistent with measures of overconfidence serving as a signal of ability. In the second set of analyses, I find that some purported associations between overconfidence and other constructs could be attributed to ability instead. I close with recommendations to recognize and reduce the potential for mistaken inferences. When research indicates that differences in overconfidence are associated with other behaviors, beliefs, or evaluations, researchers should account for the possibility that differences in ability could provide a sufficient explanation. This paper was accepted by Jack Soll, behavioral economics and decision analysis. Funding: This work was supported by the UCLA Anderson Morrison Center for Marketing and Data Analytics. Supplemental Material: The online appendix and data files are available at https://doi.org/10.1287/mnsc.2024.05184 and https://researchbox.org/1597 .

**为什么推荐**

- 相关性 0/100（价格词 ×0题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 70/100（Management Science）
- 时效 86/100（上线 2 天前）
- 方法匹配 25/100（predict）
- 有摘要，可快速判断
- 有开放获取全文

[DOI / 原文](https://doi.org/10.1287/mnsc.2024.05184) ｜ [开放获取全文](https://doi.org/10.2139/ssrn.4468920)

---

## 7. When GenAI Increases Inequality: Evidence from a University Debating Competition

**Management Science** · 上线 2026-11-25（1 天前） · T1 · Antonio Roldán-Monés · 综合分 **32.9** · 强相关

**摘要**

Research on Generative AI (GenAI) and work reports both productivity-compressing and inequality-expanding effects, leaving open a central question for organizations: Who benefits from GenAI and on which specific tasks? I address this question through a randomized controlled trial in competitive university debating, where participants are randomly assigned access to GenAI. Although most previous experimental work examines the impact of GenAI on written activities and across individuals, this setting allows me to study the impact of GenAI on a knowledge-intensive spoken activity and to identify heterogeneous effects across subtasks. I find that GenAI expands performance inequality in this setting. Consistent with recent theories on GenAI and work, results show that high-ability participants experience significantly larger gains from GenAI usage than their lower-ability counterparts in judgment-intensive subtasks, whereas lower-ability individuals only improve their performance in less expert components of debating, where GenAI can be used as a substitute. If these inequality-expanding effects generalize to similar spoken settings where complex ideas must be internalized and explained, rather than simply written, they would have important implications for understanding the impact of GenAI on work and inequality. This paper was accepted by Maria Guadalupe, business strategy. Supplemental Material: The online appendix and data files are available at https://doi.org/10.1287/mnsc.2025.01063 .

**为什么推荐**

- 相关性 0/100（价格词 ×0题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 70/100（Management Science）
- 时效 93/100（上线 1 天前）
- 方法匹配 0/100
- 有摘要，可快速判断

[DOI / 原文](https://doi.org/10.1287/mnsc.2025.01063)

---

## 8. Nowcasting Italian GDP Growth: A Factor MIDAS Approach

**Journal of Forecasting** · 上线 2026-11-25（1 天前） · T3 · Donato Ceci、Orest Prifti、Andrea Silvestrini · 综合分 **31.4** · 强相关

**摘要**

ABSTRACT This paper examines the role of weekly financial data in nowcasting the quarterly growth rate of Italian real GDP, with a specific focus on the impact of the Covid‐19 pandemic. It combines factor models and mixed data sampling (MIDAS) regression models to set up Factor MIDAS specifications, which leverage a wide range of higher‐frequency financial variables to exploit the information flow within the quarter. The analysis is performed using a comprehensive dataset comprising monthly macroeconomic and weekly financial data, properly adjusted for seasonal patterns, calendar day effects, and excess volatility. The predictive accuracy is assessed by conducting a pseudo out‐of‐sample nowcast exercise and evaluating their performance with and without the inclusion of factors derived from financial indicators. Financial variables improve the nowcast of Italian real GDP growth primarily through their timeliness. The gains are concentrated in the first month of the quarter, when the macroeconomic information set is still sparse, and become smaller as monthly macroeconomic indicators are released. This suggests that financial information is especially useful as an early‐quarter signal rather than as a uniformly dominant source of independent predictive content throughout the quarter.

**为什么推荐**

- 相关性 0/100（价格词 ×0题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 25/100（Journal of Forecasting）
- 时效 93/100（上线 1 天前）
- 方法匹配 75/100（predictive、volatility、nowcasting）
- 有摘要，可快速判断

[DOI / 原文](https://doi.org/10.1002/for.70235)

---

## 9. Tourism designation and green innovation: Evidence from China’s 5A National Tourist Attractions

**Energy Economics** · 上线 2026-11-26（0 天前） · T2 · Yongji Zhang、Zifei Meng、Ke Wang、Baojun Tang · 综合分 **30.0** · 强相关

> ⚠ 该刊未向 Crossref/OpenAlex 提供摘要，本条基于标题判相关性，建议点开原文确认。

**为什么推荐**

- 相关性 0/100（价格词 ×0题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 75/100（Energy Economics）
- 时效 100/100（上线 0 天前）
- 方法匹配 0/100

[DOI / 原文](https://doi.org/10.1016/j.eneco.2026.109724)

---

## 10. Quantile forecast combination: An application to forecasting US GDP growth

**International Journal of Forecasting** · 上线 2026-11-26（0 天前） · T2 · Knut Are Aastveit、Saskia ter Ellen、Giulia Mantoan · 综合分 **30.0** · 强相关

> ⚠ 该刊未向 Crossref/OpenAlex 提供摘要，本条基于标题判相关性，建议点开原文确认。

**为什么推荐**

- 相关性 0/100（价格词 ×0题名 / ×0摘要；商品期货词 ×0题名）
- 期刊权重 50/100（International Journal of Forecasting）
- 时效 100/100（上线 0 天前）
- 方法匹配 50/100（forecast、forecasting）

[原文页面](https://www.sciencedirect.com/science/article/pii/S0169207026000580)

---

## 抓取覆盖情况

| 期刊 | 方向 | 窗口内新文 | 本期入选 |
| --- | --- | --- | --- |
| Energy Economics | 能源资源 | 76 | 1 |
| International Journal of Forecasting | 计量预测 | 62 | 2 |
| Food Policy | 农业商品 | 46 | 0 |
| Management Science | 金融经济 | 35 | 5 |
| Journal of Econometrics | 计量预测 | 30 | 0 |
| Journal of Environmental Economics and Management | 能源资源 | 27 | 0 |
| Journal of Financial Economics | 金融经济 | 18 | 0 |
| Econometrica | 金融经济 | 17 | 0 |
| Resource and Energy Economics | 能源资源 | 14 | 0 |
| Journal of Commodity Markets | 农业商品 | 14 | 0 |
| Journal of Forecasting | 计量预测 | 5 | 1 |
| Review of Financial Studies | 金融经济 | 4 | 0 |
| The Quarterly Journal of Economics | 金融经济 | 3 | 1 |
| American Journal of Agricultural Economics | 农业商品 | 2 | 0 |
| The Energy Journal | 能源资源 | 1 | 0 |
| The Journal of Finance | 金融经济 | 0 | 0 |
| American Economic Review | 金融经济 | 0 | 0 |

数据源：OpenAlex（主）+ Crossref（兜底）。抓取时间 2026-11-26 08:41:41。
