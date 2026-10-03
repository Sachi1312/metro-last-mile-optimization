# Literature review

Screened set: the 9 papers already cited in the project report, plus 16 further papers on station access, mode choice, and metro demand in India or in comparable urban rail systems. The discussion below keeps the 12 that change what this project should claim. Papers that are single-city descriptive studies, or that never connect access quality to an operational decision, are listed and then set aside.

## What the useful papers agree on

Last-mile pain is mostly access time, reliability, and the quality of the walk or feeder, not the metro ride itself. Brons, Givoni, and Rietveld (2009) and Givoni and Rietveld (2007) show that satisfaction and rail use move with the access trip. Krygsman, Dijst, and Arentze (2004) separate the access, egress, and transfer pieces of a multimodal journey instead of treating the trip as one mode. That split is why this project keeps a station-level last-mile score rather than a city-wide mode share.

Indian work makes the same point with local modes. Goel and Tiwari (2016) describe how Delhi metro users actually reach stations, including walk, cycle, rickshaw, and feeder modes. Rastogi and Rao (2003) do the same for Mumbai commuters accessing transit. Bajaj and Singh (2021) measure Delhi mode preferences with a survey, but stop at the preference model: there is no forecast and no intervention ranking. Chatterjee and Paul (2022) and Saif and Anupam (2025) name the Indian last-mile problem and stay at the level of a review or a strategy note.

## What this project takes from them

| Paper | What is used | What it does not do |
|---|---|---|
| Bajaj and Singh (2021) | Survey design for mode preference | No forecast, Delhi only |
| Chatterjee and Paul (2022) | The dimensions behind an LMPI-style index | No measured model |
| Goel and Tiwari (2016) | Delhi access modes, used as context for the Delhi scenario | Not a multi-line optimizer |
| Rastogi and Rao (2003) | Mumbai access behavior | One access study, no pipeline |
| Brons, Givoni, and Rietveld (2009) | Access quality changes rail use | European rail, not a metro classifier |
| Givoni and Rietveld (2007) | Access trip drives satisfaction | No station ranking |
| Krygsman, Dijst, and Arentze (2004) | Access, egress, and transfer as separate times | No Indian metro data |
| Iseki and Taylor (2009) | Transfers are not equal; wait and walking matter | Framework, not a forecast |
| Cervero (2001) | Walk access depends on the street and the stop | US cases |
| Boarnet et al. (2017) | First and last mile is also an equity question | US planning |
| Kalašová, Čulík, and Poliak (2022) | First/last mile connection to public transport | Slovakia, survey logic |
| Saki and Soori (2025) | Compare ML families rather than trust one score | Review, not an implementation |

## Papers screened and not written up in full

These were read for scope and then left out of the main argument because they do not add a method this pipeline uses:

- Chen et al. (2025) on bike-share and bus competition at metro stations. Useful context, one city, no end-to-end optimizer.
- Kalboussi, Ndhaief, and Rezg (2024) on neural nets for last-mile routing. Different decision from station severity.
- Altaf and Biyani (2023), Opti-Mile. Path planning, not a station index.
- Liu et al. (2025) on autonomous-vehicle scheduling. Different fleet problem.
- Hall, Palsson, and Price (2018) on ride-hailing and transit. City-level substitution, not station operations.
- Zhao and Li (2017) on bicycle-metro integration in Beijing. One access mode.
- Tilahun et al. (2016) on last-mile issues and the work commute. US commute survey.
- Pucher, Korattyswaroopam, and Ittyerah (2004) and Singh (2005) on the state of Indian urban transport. Background only.
- Tiwari (2002) on urban transport priorities in developing cities. Policy framing.
- Badami and Haider (2007) on bus performance in Indian cities. Bus operations, not metro stations.
- Keijer and Rietveld (2000) on how people reach Dutch railway stations. Same access question, older European data.
- Shaheen and Chan (2016) on shared mobility as a first/last-mile feeder. No station classifier.
- Cervero and Kockelman (1997) on density, diversity, and design. Land use, used only as a reason to keep population and walk distance as inputs.
- Bhandari, Kato, and Hayashi (2009) on equity impacts of Delhi Metro. Impact evaluation, not an operating tool.
- Advani and Tiwari (2005) on evaluating Delhi Metro as a system. System review, not station-level actions.

## Gap this project is answering

None of the screened papers run classification, a footfall forecast, and an intervention ranking as one pipeline on more than one Indian metro line. Several are honest about being surveys or reviews. This project should be equally honest: the LMPI number is a formula in the tradition of the review papers, and the model result is only a finding when it is not asked to repeat that formula.

## References

Advani, M., & Tiwari, G. (2005). Evaluation of public transport systems: Case study of Delhi Metro. *Proceedings of the START Conference*.

Altaf, R., & Biyani, P. (2023). No transfers required: Integrating last mile with public transit using Opti-Mile. *IEEE ITSC*.

Badami, M. G., & Haider, M. (2007). An analysis of public bus transit performance in Indian cities. *Transportation Research Part A*, 41(10), 961–981.

Bajaj, G., & Singh, P. (2021). Understanding preferences of Delhi metro users using choice-based conjoint analysis. *IEEE Transactions on Intelligent Transportation Systems*, 22(1), 384–398.

Bhandari, K., Kato, H., & Hayashi, Y. (2009). Economic and equity evaluation of Delhi Metro. *International Journal of Urban Sciences*, 13(2), 187–203.

Boarnet, M. G., Giuliano, G., Hou, Y., & Shin, E. J. (2017). First/last mile transit access as an equity planning issue. *Transportation Research Part A*, 103, 296–310.

Brons, M., Givoni, M., & Rietveld, P. (2009). Access to railway stations and its potential in increasing rail use. *Transportation Research Part A*, 43(2), 136–149.

Cervero, R. (2001). Walk-and-ride: Factors influencing pedestrian access to transit. *Journal of Public Transportation*, 3(4), 1–23.

Cervero, R., & Kockelman, K. (1997). Travel demand and the 3Ds: Density, diversity, and design. *Transportation Research Part D*, 2(3), 199–219.

Chatterjee, A., & Paul, S. K. (2022). Last mile connectivity in the Indian scenario: A literary review. *International Journal of Transportation Engineering and Technology*, 8(2), 45–52.

Chen, T., Chen, Y., Mou, Z., & Yu, X. (2025). The game relationship of metro station connection mode. *IEEE Access*, 13, 70128–70140.

Givoni, M., & Rietveld, P. (2007). The access journey to the railway station and its role in passengers’ satisfaction with rail travel. *Transport Policy*, 14(5), 357–365.

Goel, R., & Tiwari, G. (2016). Access–egress and other travel characteristics of metro users in Delhi and its satellite cities. *IATSS Research*, 39(2), 164–172.

Hall, J. D., Palsson, C., & Price, J. (2018). Is Uber a substitute or complement for public transit? *Journal of Urban Economics*, 108, 36–50.

Iseki, H., & Taylor, B. D. (2009). Not all transfers are created equal. *Transport Reviews*, 29(6), 777–800.

Kalašová, A., Čulík, K., & Poliak, M. (2022). The importance of connecting the first/last mile to public transport. *Transportation Research Procedia*, 62, 225–232.

Kalboussi, E., Ndhaief, N., & Rezg, N. (2024). Last-mile optimization using neural networks. *Computers & Industrial Engineering*, 187, 109824.

Keijer, M. J. N., & Rietveld, P. (2000). How do people get to the railway station? The Dutch experience. *Transportation Planning and Technology*, 23(3), 215–235.

Krygsman, S., Dijst, M., & Arentze, T. (2004). Multimodal public transport: An analysis of travel time elements and the interconnectivity ratio. *Transport Policy*, 11(3), 265–275.

Liu, Y., Xie, B., Long, Y., Chen, J., & Xu, G. (2025). Learning-based heterogeneous autonomous vehicles scheduling for on-demand last-mile transportation. *IEEE Transactions on Automation Science and Engineering*, 22, 20119–20125.

Pucher, J., Korattyswaroopam, N., & Ittyerah, N. (2004). The crisis of public transport in India. *Journal of Public Transportation*, 7(4), 1–20.

Rastogi, R., & Krishna Rao, K. V. (2003). Travel characteristics of commuters accessing transit: Case study. *Journal of Transportation Engineering*, 129(6), 684–694.

Saif, H., & Anupam, A. (2025). Strategy to enhance last mile connectivity of metro rail transit system in India. *Journal of Urban Transport and Infrastructure*, 4(1), 12–21.

Saki, S., & Soori, M. (2025). Artificial intelligence, machine learning and deep learning in advanced transportation systems: A review. *Transportation Engineering*, 16, 100255.

Shaheen, S., & Chan, N. (2016). Mobility and the sharing economy: Potential to facilitate the first- and last-mile public transit connections. *Built Environment*, 42(4), 573–588.

Singh, S. K. (2005). Review of urban transportation in India. *Journal of Public Transportation*, 8(1), 79–97.

Tilahun, N., Thakuriah, P., Li, M., & Keita, Y. (2016). Transit use and the work commute: Analyzing the role of last mile issues. *Journal of Transport Geography*, 54, 359–368.

Tiwari, G. (2002). Urban transport priorities: Meeting the challenge in developing countries. *Cities*, 19(2), 95–103.

Zhao, P., & Li, S. (2017). Bicycle-metro integration in a growing city. *Transportation Research Part A*, 99, 46–60.
