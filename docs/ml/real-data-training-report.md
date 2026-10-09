# D70 real NSE research training

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION.
NOT PRODUCTION PIT; historical revision timing remains unknown.
Assumed availability is the next research session's pre-open stage, never
verified exchange publication. Results are NOT PRODUCTION-VALIDATED.
P1_PRODUCTION_DATA_CLEARANCE = OPEN; PRODUCTION_MARKET_DATA_USE = NOT_CLEARED.
Fundamentals and genuine benchmark comparison remain UNAVAILABLE.

Feature rows: 6,827,699. Model fits: 152.
All six classification and six regression families use identical eligible
rows/features within each horizon/fold. The fixed existing arena uses seed
1729 and 32 tree/boosting iterations, with no tuning search. Forest fitting
uses the recorded four-thread allocation; prediction remains serial and
other estimator inner threads remain one. Exact real-data forest parity
is recorded in real-forest-execution-parity.json.
This small baseline arena is not a claim of optimal model capacity.
2010-2014 are retained for warm-up; expanding training starts in 2015.
2022-2024 are development OOS, 2025 confirmation, 2026 final holdout.
All preprocessing is freshly fitted on past training rows only.

| Feature | Available | Unavailable | Availability % |
| --- | --- | --- | --- |
| atr_14 | 5777150 | 1050549 | 84.6134 |
| bollinger_location_20 | 6267210 | 560489 | 91.791 |
| bollinger_width_20 | 6267305 | 560394 | 91.7923 |
| close_to_high_20 | 6267305 | 560394 | 91.7923 |
| distance_sma_10 | 6488592 | 339107 | 95.0334 |
| distance_sma_100 | 4992050 | 1835649 | 73.1147 |
| distance_sma_20 | 6267305 | 560394 | 91.7923 |
| distance_sma_200 | 3783128 | 3044571 | 55.4085 |
| distance_sma_5 | 6630185 | 197514 | 97.1072 |
| distance_sma_50 | 5737891 | 1089808 | 84.0384 |
| drawdown_20 | 6267305 | 560394 | 91.7923 |
| ema_12 | 5780972 | 1046727 | 84.6694 |
| ema_26 | 5764152 | 1063547 | 84.4231 |
| log_return_1 | 6751474 | 76225 | 98.8836 |
| macd | 5754917 | 1072782 | 84.2878 |
| macd_histogram | 5754917 | 1072782 | 84.2878 |
| macd_signal | 5754917 | 1072782 | 84.2878 |
| momentum_percentile_20 | 6247227 | 580472 | 91.4983 |
| range_location_20 | 6267195 | 560504 | 91.7907 |
| return_1 | 6751474 | 76225 | 98.8836 |
| return_10 | 6464001 | 363698 | 94.6732 |
| return_20 | 6247227 | 580472 | 91.4983 |
| return_5 | 6598352 | 229347 | 96.6409 |
| return_60 | 5564361 | 1263338 | 81.4969 |
| rsi_14 | 5777150 | 1050549 | 84.6134 |
| sma_10 | 6488592 | 339107 | 95.0334 |
| sma_100 | 4992050 | 1835649 | 73.1147 |
| sma_20 | 6267305 | 560394 | 91.7923 |
| sma_200 | 3783128 | 3044571 | 55.4085 |
| sma_5 | 6630185 | 197514 | 97.1072 |
| sma_50 | 5737891 | 1089808 | 84.0384 |
| volatility_10 | 6464001 | 363698 | 94.6732 |
| volatility_20 | 6247227 | 580472 | 91.4983 |
| volatility_5 | 6598352 | 229347 | 96.6409 |
| volatility_60 | 5564361 | 1263338 | 81.4969 |
| volume_ratio_20 | 6267305 | 560394 | 91.7923 |
| volume_sma_20 | 6267305 | 560394 | 91.7923 |
| volume_zscore_20 | 6267301 | 560398 | 91.7923 |

Benchmark-relative strength/market context and fundamentals are unavailable
and excluded from X. Momentum percentile uses contemporaneous candidate
peers only. Missing required slots remain null, including SMA100/SMA200
windows crossing missing Muhurat prices. Degraded inputs retain their states
under the explicit existing ALLOW_DEGRADED policy.

2011 has zero available SMA200/full-feature training rows. Its source
ISIN fields are absent through June 21 and present from June 22; the
conservative identity histories remain separate, without future backfill.
See ../data/research-identity-availability-impact.json for the source hash
and observed counts. Uneven annual eligibility is not silently repaired.

| Horizon | Mature | Unavailable | Not yet mature | Training eligible | Candidate rows with missing required Muhurat slot |
| --- | --- | --- | --- | --- | --- |
| 1 | 6751474 | 71037 | 5188 | 3758919 | 1641485 |
| 5 | 6598352 | 213827 | 15520 | 3664280 | 1673681 |
| 10 | 6464001 | 335294 | 28404 | 3548331 | 1713921 |
| 20 | 6247227 | 526408 | 54064 | 3326667 | 1794042 |

Missing-slot impact counts may overlap other insufficiencies; they are not
causal counterfactual counts. Authoritative terminal events remain unavailable,
rather than being invented from disappearance. P7 targets preserve exact
Decimal numerator/denominator; conversion occurs at the estimator boundary.

| Horizon | Unadjusted-action outcome exclusions |
| --- | --- |
| 1 | 20425 |
| 5 | 99920 |
| 10 | 197107 |
| 20 | 383680 |

Action-affected available feature windows are quantified separately in
../data/research-corporate-action-impact.json. Counts overlap other quality
and missingness causes; they are not additive or adjustment factors.

| Phase | Horizon | Task | Family | Fold | Training | OOS | Scored | Run ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| development | 1 | classification | logistic | 2022 | 1481917 | 393027 | 391640 | 05cb29c3407bc7c12f654e32310316ea10c0de3eee5b3163fbe4f10f67bf852b |
| development | 1 | classification | random_forest | 2022 | 1481917 | 393027 | 391640 | 9616a3358ed250933852339d805038f58d682d428590bc7dadfbead23602d418 |
| development | 1 | classification | hist_gradient_boosting | 2022 | 1481917 | 393027 | 391640 | 7b5d2913fb1544dccf9b6b6a59fc13448b42f6bd3b78e926eac43dd3c200579c |
| development | 1 | classification | lightgbm | 2022 | 1481917 | 393027 | 391640 | 9f332da0973b9ebc5caa4dee5f1678fb1270dbfdfe36741f2303df1abfe0968e |
| development | 1 | classification | catboost | 2022 | 1481917 | 393027 | 391640 | a726614967fa339d4f02d195d97329ee740de60db1a31a089c941b9eaac8b51b |
| development | 1 | classification | xgboost | 2022 | 1481917 | 393027 | 391640 | cdedde2e3597792297d8e2d9ccc38dae4fbe7768f36f27feed3e886b909c7aa1 |
| development | 1 | classification | logistic | 2023 | 1873327 | 353940 | 350850 | badd9be8d2c3d4acc8fe60c657b01b95fca0799e6ffd2203ddc0e50ef12c689e |
| development | 1 | classification | random_forest | 2023 | 1873327 | 353940 | 350850 | 330d8e9829adc8eef516bf1b51dc9e9136273793662572c6c6eb9af2d3ce530a |
| development | 1 | classification | hist_gradient_boosting | 2023 | 1873327 | 353940 | 350850 | 5d936cea39cfebfc188a0d04eb2b7a7b6fab42bd73ecd2d4c693a16b1c05b584 |
| development | 1 | classification | lightgbm | 2023 | 1873327 | 353940 | 350850 | dd5c1347cd8ea91a40b9db1d54e6a0d6e1fb85590f0c3f134c8c6c9133ed0d95 |
| development | 1 | classification | catboost | 2023 | 1873327 | 353940 | 350850 | 782a5b95c755b7ef8f0d4cd6ca71748d9591991e60ef707460a6a77a082392ba |
| development | 1 | classification | xgboost | 2023 | 1873327 | 353940 | 350850 | 878e194ffc03ca68abf06da2e3fde67412b4b7fa8b4f2c87f9b2b9ac7ec47ba2 |
| development | 1 | classification | logistic | 2024 | 2227472 | 143125 | 138965 | ed156dc6d6e66d0ad77ebd0dbd55da520bb42c81331a3a27b24f5df499e325a5 |
| development | 1 | classification | random_forest | 2024 | 2227472 | 143125 | 138965 | 2c4f8e85c04089f9873bbc926641d439f0340eeb60f7347d46a6ad7c3b05478a |
| development | 1 | classification | hist_gradient_boosting | 2024 | 2227472 | 143125 | 138965 | 3e6603d097d2b561b5e3f13f2fe81c96c1b55382d45bb1fac16afc37c579201a |
| development | 1 | classification | lightgbm | 2024 | 2227472 | 143125 | 138965 | 91bafd3950e2756c9aa434e63f5fbcc0b73cd7f6f663d6639f724dc5050a2a31 |
| development | 1 | classification | catboost | 2024 | 2227472 | 143125 | 138965 | 52141368f6ee39cce46620d178bd6172e891237290d6fb6cbb3debed2eebe340 |
| development | 1 | classification | xgboost | 2024 | 2227472 | 143125 | 138965 | 15c756ab4702c1b0119e9578cffbd7e9a7e8c000437dde2d08bd9c4e95118455 |
| development | 1 | regression | ridge | 2022 | 1481917 | 393027 | 391640 | f15fbbed76491a9f0c81845ae2c09d83c36dace0c90e92fc4780603df3908497 |
| development | 1 | regression | random_forest | 2022 | 1481917 | 393027 | 391640 | b1c1c4f31fe5a3affaa24dde4d572f696973e0dbf91ba98735cf8f33539fb05e |
| development | 1 | regression | hist_gradient_boosting | 2022 | 1481917 | 393027 | 391640 | d17d94ba01b243e587c7103307adf0e985c7500a6f7470884033fcfaeacc1213 |
| development | 1 | regression | lightgbm | 2022 | 1481917 | 393027 | 391640 | 107eb8f103372f5f189bb88ff5f271489fd36b3deb36c07ffe9bfb06bf48d73a |
| development | 1 | regression | catboost | 2022 | 1481917 | 393027 | 391640 | a9bedbbb4d1c3df648c7ced58601c21187a8cb5d5804b729b4c219272d8e2505 |
| development | 1 | regression | xgboost | 2022 | 1481917 | 393027 | 391640 | 5a52786a68f17deed8007186860c5bec4407109d3695e6fcf9da8b4ef22ff638 |
| development | 1 | regression | ridge | 2023 | 1873327 | 353940 | 350850 | c528f7cb84935afc51ff7dcd79ea150e267d5305ca411f0c082a6c10548f4e70 |
| development | 1 | regression | random_forest | 2023 | 1873327 | 353940 | 350850 | 08c64ed4957cfcc727efba44b4af31e5c6f72bfeba3a4351988ef382439b3c6d |
| development | 1 | regression | hist_gradient_boosting | 2023 | 1873327 | 353940 | 350850 | 32985dccd32a3ec563b15a78c21597889c62ffc40dcde365cc31f6ed4ae60298 |
| development | 1 | regression | lightgbm | 2023 | 1873327 | 353940 | 350850 | 6a81d32e2ef5c79ad91525b81cfabb735b9937a75fe8ae585d2738c84fe54524 |
| development | 1 | regression | catboost | 2023 | 1873327 | 353940 | 350850 | 0028b310d0defdfbb4fdf6bab5ba3823e1be7d594aaaf1c0538bbc445967fa0d |
| development | 1 | regression | xgboost | 2023 | 1873327 | 353940 | 350850 | 6820819f1f6e5f83a5354c088ac4bb0c5947dba97672eb46f8fafc1249772a3d |
| development | 1 | regression | ridge | 2024 | 2227472 | 143125 | 138965 | 43f7910362d970f776769d155f6ce5d8238821aef52056f85b7eac4ee6d3fea4 |
| development | 1 | regression | random_forest | 2024 | 2227472 | 143125 | 138965 | fbed415233a28f6d37e61e326d3ddf261ce2071d80574924b91669bc977cddc5 |
| development | 1 | regression | hist_gradient_boosting | 2024 | 2227472 | 143125 | 138965 | 5a4ff946490e196915236e565d9347a739b98b73357b8a5404c855e64302376e |
| development | 1 | regression | lightgbm | 2024 | 2227472 | 143125 | 138965 | 2a1735b2540d77f84ac1202877a8b7c1030a3c46ddca872d504cff8d9e2c4ae4 |
| development | 1 | regression | catboost | 2024 | 2227472 | 143125 | 138965 | 0f0768cba4dba31303d837f43d5439e08e24ae8a1c12156ef124c4e4d0956334 |
| development | 1 | regression | xgboost | 2024 | 2227472 | 143125 | 138965 | 11ebcf265a3b4de5171b168be1b0362e789fddc9a1c0463b8eaa6256e154e45d |
| development | 5 | classification | logistic | 2022 | 1438583 | 393027 | 386253 | 0b2d3715d34c5c46c15c6f0eb0263655b97a91c224565791306fc09658c25222 |
| development | 5 | classification | random_forest | 2022 | 1438583 | 393027 | 386253 | 1d85110ba986a9a52bdc5f4192ea69e7e2b62a47b84d28b3fb78893e6c4ef628 |
| development | 5 | classification | hist_gradient_boosting | 2022 | 1438583 | 393027 | 386253 | 17522727b5839382fdfcbc823af01735401579900492f90c0ee22a4e056d9cbf |
| development | 5 | classification | lightgbm | 2022 | 1438583 | 393027 | 386253 | db12e9713b4168cbe6eedcd7b73e82128dbbb4e6e914012cbd10b27c2476f87f |
| development | 5 | classification | catboost | 2022 | 1438583 | 393027 | 386253 | f5c0eb9c05d431530ba15f714ea9424127f604b2175ac8a08ebd8d867a77471f |
| development | 5 | classification | xgboost | 2022 | 1438583 | 393027 | 386253 | 58a4f60966ddff828c27a1ecaefffaee2b9e1c33a89227ff95a65c68a894355f |
| development | 5 | classification | logistic | 2023 | 1824132 | 353940 | 338587 | 23aabadd1e48b2fdf4b5e34f9f2d946150a8d561ccf63d914dd29c3eee6a9423 |
| development | 5 | classification | random_forest | 2023 | 1824132 | 353940 | 338587 | 2390b3ef9ef0c337c3a7a1c9b3229619ff820c0fbadbd98044c53d2f97a69941 |
| development | 5 | classification | hist_gradient_boosting | 2023 | 1824132 | 353940 | 338587 | 7f7c960ebe06a08480b84d515fb94f0a317669c89e048524897609fa76d28c77 |
| development | 5 | classification | lightgbm | 2023 | 1824132 | 353940 | 338587 | 9280b6ecef7ed0788c44d5c7e241e01b8da9b4d6663dac46a4e2c3bb27c5bdc6 |
| development | 5 | classification | catboost | 2023 | 1824132 | 353940 | 338587 | 976d6b3abc06721d0882f6f58efd377908bfe1791c21299b5d9b7718542df44c |
| development | 5 | classification | xgboost | 2023 | 1824132 | 353940 | 338587 | 2d4e2e5016f9f2b0b4e8547cbacef53799fd890d4a5fc3cb5b7057cba7274be2 |
| development | 5 | classification | logistic | 2024 | 2172586 | 143125 | 129821 | 225f6777277a4700b73a79185f7c03a38ea73104146c374e2e240559bfa6e2a6 |
| development | 5 | classification | random_forest | 2024 | 2172586 | 143125 | 129821 | 093fc3fe751a0df409b532857b8b41370d725eee2004389ec99a4a95f438648f |
| development | 5 | classification | hist_gradient_boosting | 2024 | 2172586 | 143125 | 129821 | c9f3ef95b021fde0e42849d1228ccab56b48de176c9c13bdfb8bdb0341f5eb3f |
| development | 5 | classification | lightgbm | 2024 | 2172586 | 143125 | 129821 | e5383c6a9d04cc909333b58597e2b038ec2b97d4a8c9c3a0a14705425b55c4a4 |
| development | 5 | classification | catboost | 2024 | 2172586 | 143125 | 129821 | 55f392a596975ea11432d8659ac40514f7cccee9e8b13e580f19f39f4d43a121 |
| development | 5 | classification | xgboost | 2024 | 2172586 | 143125 | 129821 | 1b605196abec2feb2e74fcc8f59220751be72a908d0e7134a9c2b6c046d17c93 |
| development | 5 | regression | ridge | 2022 | 1438583 | 393027 | 386253 | 85466d22d3a631bbfa694424723c4501dd1769e61ae8f4fe85371b5be75482bc |
| development | 5 | regression | random_forest | 2022 | 1438583 | 393027 | 386253 | 1cee6b92611425d961d1e73c33cccf0ca38b9c95aec94e5de7919413a34127d6 |
| development | 5 | regression | hist_gradient_boosting | 2022 | 1438583 | 393027 | 386253 | 48a4c21efd67ba9fd647169a640fe258814d03f0eb58e64aa57df0e606cce787 |
| development | 5 | regression | lightgbm | 2022 | 1438583 | 393027 | 386253 | e9cf971f431b1fa6b39e100f60421c35818d8f467846828c8c28ee04ce41f754 |
| development | 5 | regression | catboost | 2022 | 1438583 | 393027 | 386253 | a046aa11503de5d0987f903ebd033884aee22b1b8786ab8352742566df9a3ec8 |
| development | 5 | regression | xgboost | 2022 | 1438583 | 393027 | 386253 | 9225ab583e2f54cb14c64d40e7de46e9a5c3f79b52fd6000821ab33aa6ef639a |
| development | 5 | regression | ridge | 2023 | 1824132 | 353940 | 338587 | 84091403de192edad1afcdd321caeb6abed5f630ae32b9b0e9bdd2dea621d241 |
| development | 5 | regression | random_forest | 2023 | 1824132 | 353940 | 338587 | ece2733508c6f84444d3f4a434fbcf80339dcc5a71d04a1efd340659ba83a77a |
| development | 5 | regression | hist_gradient_boosting | 2023 | 1824132 | 353940 | 338587 | 6325e97f0071a353643e59d84178b7e03fcb6d1baaf2fa2b8ff5cd991f1e1bbd |
| development | 5 | regression | lightgbm | 2023 | 1824132 | 353940 | 338587 | 48244ea607ee414bd7cb11b66594a8e43d75f8c96aca3e7be2ac5c0df0f13589 |
| development | 5 | regression | catboost | 2023 | 1824132 | 353940 | 338587 | 83cbd579223c322bf9739a7c7f9015617d7c86a2bed4e43d1b455b5dc8e4e66d |
| development | 5 | regression | xgboost | 2023 | 1824132 | 353940 | 338587 | ae837e20937a64091476cf1ead155e69ddc25771b1cb799534b86ec359bfc621 |
| development | 5 | regression | ridge | 2024 | 2172586 | 143125 | 129821 | a30cf5d9d2feb8c633390125a4aeaba226d81daf3d0f023e16c9be19524fa6ef |
| development | 5 | regression | random_forest | 2024 | 2172586 | 143125 | 129821 | 26b1e42d0ce1bfae137528566edaa2a455c55a405e5cf69f6aca101ace3b4f95 |
| development | 5 | regression | hist_gradient_boosting | 2024 | 2172586 | 143125 | 129821 | b4e43142e53b4345ed38ca14b4435ca6d77007329f43fd818f25853dc8128d31 |
| development | 5 | regression | lightgbm | 2024 | 2172586 | 143125 | 129821 | 8eeb00132c9b36fa871f591070d73cfaa05a6cf1a9be51e27cd5beae0ad2aae0 |
| development | 5 | regression | catboost | 2024 | 2172586 | 143125 | 129821 | 3cb3a58bc9660f006b94b9c8f73d2b01a544c40c81b9ee8babb4c350b9193e57 |
| development | 5 | regression | xgboost | 2024 | 2172586 | 143125 | 129821 | 5addcfd5cad2602654668e74b1b649ab7a88c4cc1194c4d3b7616ec64a40b441 |
| development | 10 | classification | logistic | 2022 | 1385535 | 393027 | 379571 | 21c69501930c0a6e69f2d086cffe8d45addbb730b8ad30d4a42b947ec199f166 |
| development | 10 | classification | random_forest | 2022 | 1385535 | 393027 | 379571 | c860e999a81fb2ff317ca3404f275c9beb35bcf8e60a63e08ed497f23fa34937 |
| development | 10 | classification | hist_gradient_boosting | 2022 | 1385535 | 393027 | 379571 | 90cb0fef412b804f6d2a580595e0fd772eab8feba2ebe64c46f3cbf46bf9e1c5 |
| development | 10 | classification | lightgbm | 2022 | 1385535 | 393027 | 379571 | bcdd209897bb39d096385a1cad52b925e0d58ddcac789b01f697925941c3b8e8 |
| development | 10 | classification | catboost | 2022 | 1385535 | 393027 | 379571 | c22201232fcea9f0ba5c6015cb6051ffb41e1b611f26bb95e04e4ce248b8d6b8 |
| development | 10 | classification | xgboost | 2022 | 1385535 | 393027 | 379571 | 2f6e70530360856affb24c52bdc71a0c40917e2945aebff48f111dbc02e9b569 |
| development | 10 | classification | logistic | 2023 | 1763778 | 353940 | 323428 | 1dad462143276d06286ddb2f338d1ae21978e00e0ab31c7fdab949648c74a65b |
| development | 10 | classification | random_forest | 2023 | 1763778 | 353940 | 323428 | cbae93ab203a6df4935a17d6ca39d0b54513e75cef39e21a290d6755b2f7cd8e |
| development | 10 | classification | hist_gradient_boosting | 2023 | 1763778 | 353940 | 323428 | 89dec986f851691598f0e34d052285d6916ba4ba1702674ecc7ba6ac56cb9dfd |
| development | 10 | classification | lightgbm | 2023 | 1763778 | 353940 | 323428 | cfef5f5aaf560bbb2feea5d1970e4ce5ad689d8b679bac789484c9674df2e3f1 |
| development | 10 | classification | catboost | 2023 | 1763778 | 353940 | 323428 | 93beb34372dc7a71be367d11351247428cd594afb3a1a9e1f996e8eac9ada257 |
| development | 10 | classification | xgboost | 2023 | 1763778 | 353940 | 323428 | 5724d79cc2ffdc513136baacbff858be62ff2198de66cd349755812ad762a476 |
| development | 10 | classification | logistic | 2024 | 2105254 | 143125 | 118873 | b50bb43bcd8531a2bd7bb1e87a0d65ae3ddd9223e5a970f9f52a3ec9436a4b9d |
| development | 10 | classification | random_forest | 2024 | 2105254 | 143125 | 118873 | ff6cf5d2e7a62336aeac891330dd72f4ce6f76cb18ed0f7fbd40c4e06180b0b4 |
| development | 10 | classification | hist_gradient_boosting | 2024 | 2105254 | 143125 | 118873 | 3d75c45d3b8032903d83e4e65d25bc04d2122952aa605191225fad560ee76277 |
| development | 10 | classification | lightgbm | 2024 | 2105254 | 143125 | 118873 | dce010a2058f37403fcb4131f3fe5009124d638a5e053e5fb1efa6f7089cf159 |
| development | 10 | classification | catboost | 2024 | 2105254 | 143125 | 118873 | 0c99c2970e1ae9720cde6010b9a7729ef336835324a2ec0a6f58f83d25d9e670 |
| development | 10 | classification | xgboost | 2024 | 2105254 | 143125 | 118873 | dd989b4bec00fd348a874a0a6b6dce2d1cea93a302d6717712c0f314250647b6 |
| development | 10 | regression | ridge | 2022 | 1385535 | 393027 | 379571 | 20199dfdfa9b4524721fe7355b56e86d672220f4dbe96cc188a85203d3a557ee |
| development | 10 | regression | random_forest | 2022 | 1385535 | 393027 | 379571 | 93e703f7e5ec7307dea677b1430b8d2d60c5dec7a0a6295d25fb36a06b83f236 |
| development | 10 | regression | hist_gradient_boosting | 2022 | 1385535 | 393027 | 379571 | c9b7e0cde4ee6c10212bcc29f81486e30d4b3d5fbb5aedbda302f8d17785f1ba |
| development | 10 | regression | lightgbm | 2022 | 1385535 | 393027 | 379571 | fcacbdfdca4add1e50bb8d5ec90614c8d73ce6ed28bd7a9a136f963b4e3cc859 |
| development | 10 | regression | catboost | 2022 | 1385535 | 393027 | 379571 | 96c8c23ca5821762dcfe2ec563406a5018e7ae5f8d9aaee34be923215fcbf892 |
| development | 10 | regression | xgboost | 2022 | 1385535 | 393027 | 379571 | 46812c1f6680dc1193a7ab9b3d1dfed349849e8356af328262a89abddbdd2f97 |
| development | 10 | regression | ridge | 2023 | 1763778 | 353940 | 323428 | f5aa9b9fd59e16849c666a5d4c1372726118c1db3d71e2c9bf94cdfd676bb5db |
| development | 10 | regression | random_forest | 2023 | 1763778 | 353940 | 323428 | 8f6a6239c31a98f35ecb014a91ed610edd5910ced021976ee5ba5b54531d742e |
| development | 10 | regression | hist_gradient_boosting | 2023 | 1763778 | 353940 | 323428 | f42da6f2f03e2296d5c80e4fb8041a1fa09c8de126afa2302e08859d59e93c6a |
| development | 10 | regression | lightgbm | 2023 | 1763778 | 353940 | 323428 | 253f40efbf8fac7df73225079418a49eba991c9fcfdf63829dcf112c1fc11b1b |
| development | 10 | regression | catboost | 2023 | 1763778 | 353940 | 323428 | 1cc0691ac35d55130009ae2a9c33724d2f971a9e5564de59a7beb96c7f70b63c |
| development | 10 | regression | xgboost | 2023 | 1763778 | 353940 | 323428 | 3788c7b0a0d485089b9c0dc8593395e8800c7946a11d6b3d89c2dc3c3c4d8f4d |
| development | 10 | regression | ridge | 2024 | 2105254 | 143125 | 118873 | c31e2a912f47c363a6146752317158a9b16ec7da0984a6eced01f85aae1a1705 |
| development | 10 | regression | random_forest | 2024 | 2105254 | 143125 | 118873 | a8f74e98cbccf218a0fb28077f11907ab2546636c76abc17dc5a88a1667a59d2 |
| development | 10 | regression | hist_gradient_boosting | 2024 | 2105254 | 143125 | 118873 | 3dba31ab78b57c70690e9b9c625cac7a6ed7ea5246bd67eac56aeaa4b072203d |
| development | 10 | regression | lightgbm | 2024 | 2105254 | 143125 | 118873 | a2bde053c0f12a2d22de2799d890a102e493a0692e6acef29cffb017ebc8501d |
| development | 10 | regression | catboost | 2024 | 2105254 | 143125 | 118873 | b62b18515fad335ffcb92a207ce56dfaceafe59640b331cc15420df70d91d85f |
| development | 10 | regression | xgboost | 2024 | 2105254 | 143125 | 118873 | eb323eeee1cd1b5c6d3100136b3b5a45ff769df45ae48dfa371644fa2f3596ac |
| development | 20 | classification | logistic | 2022 | 1282729 | 393027 | 366326 | 20277d75a07f099f664e6aa56aa2eec02963de8b560f3bef6220aee32eabc438 |
| development | 20 | classification | random_forest | 2022 | 1282729 | 393027 | 366326 | 3f5dfcb506cfa3048262c5a2645f45f375637014c062c7b5db8b688cd1b6cbf0 |
| development | 20 | classification | hist_gradient_boosting | 2022 | 1282729 | 393027 | 366326 | 5be110c765da1a175c00d895e656504c877c9eb393930b116fda8d3b5034c7e4 |
| development | 20 | classification | lightgbm | 2022 | 1282729 | 393027 | 366326 | 7969a7c64a425dd10f8fdec61cf73ae57b23f3bf9af5e0e6ded80751d6babb6f |
| development | 20 | classification | catboost | 2022 | 1282729 | 393027 | 366326 | 2d0fc950f48fb7aa7282bb1741d4daa80e2a6414f683c013f725a5522b553f5e |
| development | 20 | classification | xgboost | 2022 | 1282729 | 393027 | 366326 | 11d46c8ecc095fd0a31069bcbf6e0b5ba580d046eb1a09c8bb6c945a505491a4 |
| development | 20 | classification | logistic | 2023 | 1646458 | 353940 | 293610 | c507eb88e8ca380c57afc9133ed7fc3274eaeb4f952fd7517382c4990cf6d1be |
| development | 20 | classification | random_forest | 2023 | 1646458 | 353940 | 293610 | 5329d907dc1c909ab61a0d73f1c527f48c826087759467b02e29fad106ba24c8 |
| development | 20 | classification | hist_gradient_boosting | 2023 | 1646458 | 353940 | 293610 | b7e9e11dda7a7aa56a64a87355896f6dabf9171e445b7a7c908ec42ac84902af |
| development | 20 | classification | lightgbm | 2023 | 1646458 | 353940 | 293610 | edfbeab1e163dfda0570d6b71739db6ff7be731a47f182e7c22f80b2b7fe992a |
| development | 20 | classification | catboost | 2023 | 1646458 | 353940 | 293610 | 8d225d7ba58f8160fef3b79c468f193e9a7bc7ee6f54fabae91af4b2760f9dba |
| development | 20 | classification | xgboost | 2023 | 1646458 | 353940 | 293610 | 49fd10db65f68f09c682c3c9a092a533aeaf69ba6ea35fb5c520e860bef0d9a5 |
| development | 20 | classification | logistic | 2024 | 1974221 | 143125 | 98808 | 672d2ca27b2dd25f4f1d498b40834ccd155a07020d37fd3eceb1aae6b04c95b9 |
| development | 20 | classification | random_forest | 2024 | 1974221 | 143125 | 98808 | 35f9965b836ece5deda0a9bac63cf63a86c7231a9ffc8e352b50f58c995e846b |
| development | 20 | classification | hist_gradient_boosting | 2024 | 1974221 | 143125 | 98808 | 337ed386950b372bab7f629f29103b6ada74063783f5ed95747fcc52e1f2429d |
| development | 20 | classification | lightgbm | 2024 | 1974221 | 143125 | 98808 | 1fe9be7b18e3078a5b51ffed06be988f6ac014ebaf88cfb7ccca74f2892ff6b2 |
| development | 20 | classification | catboost | 2024 | 1974221 | 143125 | 98808 | ec7f3313c88b5a9da0b40e6f176ec09062656fac7a68f16dbb25522e57a564c3 |
| development | 20 | classification | xgboost | 2024 | 1974221 | 143125 | 98808 | fe4b2beb12ae9695a41ae884f2db5a7f3dafefaef12d9db6f3298dcca65814b2 |
| development | 20 | regression | ridge | 2022 | 1282729 | 393027 | 366326 | 426505e23fa8a2c935f76523c417404b91be6143353f6f63299459b121d03347 |
| development | 20 | regression | random_forest | 2022 | 1282729 | 393027 | 366326 | b24a5df7098b37a7b76374d4f80f1ed1452c702bd7d1af30d991c2231c1d1f58 |
| development | 20 | regression | hist_gradient_boosting | 2022 | 1282729 | 393027 | 366326 | 8d4047a70d7dcb15cdb822c7927abd74472a10f7544bf91ab17ad6e3729da9f6 |
| development | 20 | regression | lightgbm | 2022 | 1282729 | 393027 | 366326 | c7a0d9fcd1a040119b1b3e439d17e6bedbf1f9583f34ae34b1c8e4577f46c098 |
| development | 20 | regression | catboost | 2022 | 1282729 | 393027 | 366326 | 5b29208686dc6cc38e5fe68f8a5d5449adef7b08c7188de26432e523864cd759 |
| development | 20 | regression | xgboost | 2022 | 1282729 | 393027 | 366326 | 70c6722636aff59fe9b28a5efd436f34c6ff32175f32b2fcfd79a9ec249c3eb0 |
| development | 20 | regression | ridge | 2023 | 1646458 | 353940 | 293610 | e8b681d85c0e02827437f89cb95e6abb2fbf65db66e3e4e0f381bdd51df22437 |
| development | 20 | regression | random_forest | 2023 | 1646458 | 353940 | 293610 | 2bde9278c332abe6a47042d3974fdabb4e1d141f3b110337ed803dd24e362459 |
| development | 20 | regression | hist_gradient_boosting | 2023 | 1646458 | 353940 | 293610 | a609130e70c860a0d608729cc71538943b1e6eb5d9df24def31389cf7b07f8e3 |
| development | 20 | regression | lightgbm | 2023 | 1646458 | 353940 | 293610 | bf40403c183ae74ba683e462037ba93ac7be1f5bb56b8e83e00ec90c51513f46 |
| development | 20 | regression | catboost | 2023 | 1646458 | 353940 | 293610 | 090d330120f7bb379a67b4f8a2b5f2761066cc025d54f963297deba18d24e3ae |
| development | 20 | regression | xgboost | 2023 | 1646458 | 353940 | 293610 | 3be0414bfb3cd84cf5f9caecbb2610f9d0c817e396c34dc415b8592d685a1100 |
| development | 20 | regression | ridge | 2024 | 1974221 | 143125 | 98808 | fc41b520b6bb3d59e0de9be192ef61571db65abade4cc1ef145e4142a19895dd |
| development | 20 | regression | random_forest | 2024 | 1974221 | 143125 | 98808 | 4982ef7c481825a37bd4e5df1e27c3d7bf75bdf07575982d883f0fe6667caebd |
| development | 20 | regression | hist_gradient_boosting | 2024 | 1974221 | 143125 | 98808 | 100e948f36d981e81a79d9f69b65ebcf4143f8c5e8c7d42c6b75caf25ffdb127 |
| development | 20 | regression | lightgbm | 2024 | 1974221 | 143125 | 98808 | 1cb601e8f0d80f684cc1d2c4bdd6b853448b96ed536c7c518fd66eadd96540fa |
| development | 20 | regression | catboost | 2024 | 1974221 | 143125 | 98808 | d4fc2e36f5895d1edce91db45e0711430722f50163599ad4bb76018c8ec49665 |
| development | 20 | regression | xgboost | 2024 | 1974221 | 143125 | 98808 | 1a74e2bb56090ca034577fd651de1f8c39c71e582dc74591fb5b66bbca5a47a8 |
| 2025 | 1 | classification | hist_gradient_boosting | 2025 | 2364624 | 469571 | 463967 | 464a9b6c346a6d87f63e5fea83cc85473dca813369a6a2d063b32dbe5ee4c4df |
| 2025 | 5 | classification | hist_gradient_boosting | 2025 | 2300601 | 469571 | 449480 | 62fe958f732638892c91027358ad999c14aef3451ae0210a461700aa44cf16f4 |
| 2025 | 10 | classification | xgboost | 2025 | 2222326 | 469571 | 431506 | de86780084d6fbae919c9c0cf5178ce0c3d0c054586acf3324c6b8dbe59730d2 |
| 2025 | 20 | classification | hist_gradient_boosting | 2025 | 2071240 | 469571 | 396136 | 6b353dee369b91eeb7cfba151a5329a52adcb8c9dd407a11575838d80c6f5bcc |
| 2026 | 1 | classification | hist_gradient_boosting | 2026 | 2832062 | 367372 | 363765 | fef6c043cc51aec6f4885243fb035a771ea1a9b07ed4c4cdbf3f628fd5840893 |
| 2026 | 5 | classification | hist_gradient_boosting | 2026 | 2760783 | 367372 | 349367 | fc0ff27eff67a52e160e58d7f0627416d7fc1cabd7090268f51b17a8038d6947 |
| 2026 | 10 | classification | xgboost | 2026 | 2673513 | 367372 | 331528 | 204d32054711122c672c793ce35b0d360e5f8598df87b8cd79924a733e10d679 |
| 2026 | 20 | classification | hist_gradient_boosting | 2026 | 2504813 | 367372 | 298663 | 00c5808627f3d8e8f87f26070724a0c907f817e1e831a1e765d7ea30d267103f |

real-model-runs.json pins full configurations and artifacts. Local skops bytes
preserve the first valid checksum-pinned artifact; cross-process serialization
byte identity is not claimed. No untrusted external model is loaded.

Stored optimizer diagnostics: 12/12 LogisticRegression
fits reached the frozen iteration limit. Convergence is not established
for those fits; this is a material research limitation. No iteration/solver
or candidate-policy change follows from viewing results. See
real-model-fit-diagnostics.json for exact model IDs and stored iteration
counts, read only from locally created checksum-verified sklearn models.

## Historical preparation and earlier gates

## D70 real feature and label replay completed

The accepted replay finished with native exit 0. All 64 supervised Parquet
partition hashes, row counts and research lineage were independently rechecked:
6,827,699 research-candidate rows. Frozen supervised dataset:
`f7470b6a394444e0ad06bd088808dc2f4000fa993c63de246e773657ba274ce2`.

SMA100: 4,992,050 available (73.1147%); SMA200: 3,783,128 (55.4085%).
Available includes DEGRADED context under the existing explicit ALLOW_DEGRADED
policy; this is not an upgrade of P3 quality. Missing Muhurat observations remain
missing, including the entire required trailing window. No calendar-slot skipping,
price interpolation, adjustment or fundamental/benchmark feature was introduced.
Per-feature/year/quality counts are in feature-availability.json; per-security
availability is retained locally with the frozen artifacts.

P7 training-eligible counts over all source years: 1D 3,758,919; 5D 3,664,280;
10D 3,548,331; 20D 3,326,667. These are not fold training counts: P9 additionally
requires training start 2015, chronology, label maturity, purge and embargo.
Required missing Muhurat outcome-slot label exclusions: 8,039 / 40,235 / 80,475 /
160,596 respectively; these overlap other unavailability causes. Terminal economic
evidence is unavailable, rather than a claimed zero terminal-event population.

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION.
No actual historical availability/revision-vintage reconstruction or production
PIT claim. Model training is now running under the frozen plan; actual predictive
and backtest results remain pending. Earlier preparation statuses follow historically.

## D70 training preparation

A separate final-vintage research path is now implemented. Canonical replay is
running; real feature/label generation and model training have not finished.
The original pre-results year boundaries remain unchanged. Partitioned P9 uses
the existing fixed native arena, fresh train-only preprocessing, availability
purge and one-session-day embargo. No performance, champion or calibration claim
is made before actual runs. The earlier D69 status follows as historical evidence.

# Real-data training status after D69

Source use is authorized: REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY. Public
TejHQ originals were acquired at revision 14d81bbaef8c0f8dc673fb3e3573f9e1f32bed98.
Source permission is no longer the blocking condition.

**NOT_RUN_HISTORICAL_EVIDENCE_GATE_BLOCKED**. The source has no historical
publication/availability/completion/vintage clocks; the observed calendar omits
known special sessions; dated asset-type evidence is incomplete. Unmodified
P4-P7 contracts cannot produce an eligible historical supervised matrix. No
historical clock, session, identity backfill, price or COMMON_EQUITY fact was
invented. A decoded EQ row is not automatically a common-equity training row.

P8 models trained: **0**. Planned classification families: Logistic Regression,
Random Forest, HistGradientBoosting, LightGBM, CatBoost, XGBoost. Planned regression:
Ridge and the same five tree families. Horizons: 1/5/10/20 sessions. Model IDs and
per-horizon sample counts are unavailable; there are no performance comparisons.
No research winner or production champion exists.

The [source identity](../data/dataset-identity.json) freezes revision, 35 raw
hashes, P2-P7 versions and feature definitions. It explicitly says the P7-aligned
training dataset is not ready; raw-source identity is not a supervised-matrix ID.
[Feature availability](feature-availability.json) retains each configured feature
with null unmeasured counts/percentages. SMA100/SMA200 were not computed and have
no measured availability percentage. Relative-strength/market-context benchmark
inputs and PIT fundamentals remain UNAVAILABLE.

[Locked pre-results plan](real-research-evaluation-plan.json): 2010-2014 early
history/warm-up; 2015-2021 development training; 2022-2024 sequential development
OOS; 2025 confirmation; 2026 final holdout through the source's latest session.
Observed first/last sessions are pinned by year, not weekday assumptions. P9 must
still supply exact knowledge/maturity/purge/embargo boundaries before execution.
No model performance was inspected, no configuration was selected, and the final
holdout was not evaluated. No scaling, imputation or tuning occurred.

P11-P14 weights/thresholds remain unchanged development assumptions. P17 unstarted.
Production clearance OPEN/use NOT_CLEARED. All result JSONs distinguish NOT_RUN
from zero empirical performance. Historical audit-only status is retained below.

---

# Real-data training status

Status: **NOT_RUN_SOURCE_GATE_BLOCKED**. No new real features, labels, aligned
supervised data, model artifacts or model IDs were generated. All sample counts,
SMA100/SMA200 percentages and year/feature availability remain UNAVAILABLE.

Requested arena, once the source/P2-P7 gates pass: classification LogisticRegression,
RandomForest, HistGradientBoosting, LightGBM, CatBoost and XGBoost; regression Ridge
and the same five tree families; independent 1/5/10/20-session labels. Use identical
eligible samples/features/time rules across families, existing versioned parameters
and fresh train-only preprocessing. P8/P9 software already supports the arena;
no source bypass or new training implementation is justified by an unapproved file.

The [feature availability status](feature-availability.json),
[label distribution status](label-distribution.json) and
[model comparison status](model-comparison.json) contain null observations/results,
not fixture metrics relabeled as real evidence. No model has a real research
candidate status, and none is a PRODUCTION_CHAMPION.

Before any final-period outcomes are inspected, pin source identities and exact
chronological split/fold boundaries after permitted date coverage is profiled.
Proposed boundary principle: earlier history for warm-up/training, development
walk-forward periods through 2024, 2025 candidate confirmation and an untouched
2026 final holdout when actual coverage permits. This is not an executed P9 fold
definition; no final-period targets/metrics have been inspected and no selection
or tuning has occurred. Missing clocks/universe evidence cannot be invented to
force training eligibility. Fundamentals remain UNAVAILABLE.

Production clearance remains OPEN/use NOT_CLEARED. Existing empirical outputs
remain TEST_ONLY — NOT A PERFORMANCE CLAIM. Any later approved real research
outputs must retain RESEARCH_FIXTURE — NOT PRODUCTION VALIDATED classification.
