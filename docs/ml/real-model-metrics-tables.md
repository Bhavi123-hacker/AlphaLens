# Real NSE research metrics by model

REAL_MARKET_OBSERVATIONS / RESEARCH_ONLY / FINAL_VINTAGE_RESEARCH_ASSUMPTION.
NOT PRODUCTION PIT; results are NOT PRODUCTION-VALIDATED.
Production clearance remains OPEN and market-data use NOT_CLEARED.

Development tables below use the unweighted mean of the three locked
2022, 2023 and 2024 OOS folds. They are not pooled-sample metrics. Counts
are the summed scorable OOS observations; models within a horizon use the
same eligible samples. Probabilities, accuracy and returns use fraction
units: 0.01 return means 1%. MAE/RMSE use fractional return units.
Rank IC and top/bottom groups are daily cross-sectional target diagnostics,
then averaged across folds; they are not hypothetical net trade returns.
Naive wins compare Brier for classification and MAE for regression.
Full fold mean/median/std/best/worst and calibration bins are retained in
real-model-comparison.json and walk-forward-results.json.

## Classification — catboost

| Horizon | Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.613928 | 0.5 | 0.125 | 1.8728e-05 | 3.74504e-05 | 0.558762 | 0.431937 | 0.662304 | 0.234878 |
| 5 | 854661 | 0.564298 | 0.507475 | 0.618449 | 0.0274725 | 0.0516936 | 0.555643 | 0.491729 | 0.681722 | 0.244346 |
| 10 | 821872 | 0.555663 | 0.510915 | 0.593261 | 0.0440281 | 0.079677 | 0.551431 | 0.499024 | 0.684653 | 0.2458 |
| 20 | 758744 | 0.545187 | 0.517533 | 0.552984 | 0.112626 | 0.178612 | 0.547595 | 0.506486 | 0.687112 | 0.247021 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0997929 | -0.00151089 | -0.00692783 | 0.00541694 | 0.0869697 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.106464 | 0.00122986 | -0.00777128 | 0.00900114 | 0.0937505 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.101849 | 0.00389183 | -0.00749334 | 0.0113852 | 0.0909083 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0928706 | 0.008642 | -0.0065505 | 0.0151925 | 0.0663458 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Classification — hist_gradient_boosting

| Horizon | Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.613941 | 0.500034 | 0.333333 | 0.00014198 | 0.000283822 | 0.559843 | 0.433675 | 0.661768 | 0.234636 |
| 5 | 854661 | 0.565381 | 0.509068 | 0.626939 | 0.032866 | 0.061365 | 0.559287 | 0.49546 | 0.681208 | 0.244096 |
| 10 | 821872 | 0.557532 | 0.51411 | 0.607861 | 0.0552685 | 0.0968249 | 0.555318 | 0.504778 | 0.684123 | 0.24554 |
| 20 | 758744 | 0.546781 | 0.519281 | 0.555843 | 0.118457 | 0.187475 | 0.55312 | 0.512274 | 0.686073 | 0.246512 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.102 | -0.00145575 | -0.00690877 | 0.00545302 | 0.0893876 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.111791 | 0.00150195 | -0.00807777 | 0.00957972 | 0.100486 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.104933 | 0.00395074 | -0.00795941 | 0.0119101 | 0.0958296 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0975907 | 0.0100698 | -0.00763129 | 0.0177011 | 0.0721502 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Classification — lightgbm

| Horizon | Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.613964 | 0.500088 | 0.334898 | 0.000333902 | 0.000667064 | 0.559802 | 0.433465 | 0.66177 | 0.234637 |
| 5 | 854661 | 0.565236 | 0.508949 | 0.627022 | 0.032851 | 0.0612469 | 0.558417 | 0.494376 | 0.681299 | 0.244141 |
| 10 | 821872 | 0.557477 | 0.514303 | 0.60719 | 0.0571559 | 0.0992076 | 0.555381 | 0.503994 | 0.684104 | 0.24553 |
| 20 | 758744 | 0.546019 | 0.51894 | 0.553754 | 0.119591 | 0.188024 | 0.553259 | 0.512158 | 0.68615 | 0.246549 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.100931 | -0.00147842 | -0.00686846 | 0.00539004 | 0.0878346 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.111223 | 0.00150308 | -0.00826981 | 0.00977289 | 0.0989547 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.104788 | 0.00404553 | -0.00811359 | 0.0121591 | 0.0940531 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0984455 | 0.0099205 | -0.00762694 | 0.0175474 | 0.073144 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Classification — logistic

| Horizon | Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.613597 | 0.50007 | 0.401067 | 0.00184986 | 0.00367981 | 0.540439 | 0.416167 | 0.665097 | 0.236139 |
| 5 | 854661 | 0.558686 | 0.502498 | 0.481311 | 0.0276548 | 0.0514307 | 0.544584 | 0.472892 | 0.683672 | 0.24529 |
| 10 | 821872 | 0.547952 | 0.507657 | 0.495155 | 0.0796927 | 0.132085 | 0.543523 | 0.481752 | 0.686679 | 0.246776 |
| 20 | 758744 | 0.53663 | 0.515016 | 0.50429 | 0.176956 | 0.246523 | 0.540232 | 0.491849 | 0.690132 | 0.248458 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.083657 | -0.00179298 | -0.00612734 | 0.00433436 | 0.0710945 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.0961232 | 0.00142581 | -0.00732467 | 0.00875048 | 0.0798518 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.0973237 | 0.00494729 | -0.00783636 | 0.0127836 | 0.0840259 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0893801 | 0.0116646 | -0.00689275 | 0.0185573 | 0.074151 | 2 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Classification — random_forest

| Horizon | Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.613933 | 0.5 | 0 | 0 | 0 | 0.550041 | 0.419934 | 0.662635 | 0.235051 |
| 5 | 854661 | 0.566075 | 0.510644 | 0.622771 | 0.0401749 | 0.0731859 | 0.55075 | 0.487586 | 0.682282 | 0.244616 |
| 10 | 821872 | 0.557535 | 0.514419 | 0.575768 | 0.0650828 | 0.114292 | 0.546928 | 0.497277 | 0.685127 | 0.246024 |
| 20 | 758744 | 0.542075 | 0.516901 | 0.54518 | 0.12147 | 0.183612 | 0.538934 | 0.4984 | 0.687723 | 0.247326 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0810341 | -0.00188496 | -0.00639513 | 0.00451017 | 0.0726285 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.0912909 | 0.000859511 | -0.0067655 | 0.00762501 | 0.0784751 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.0868801 | 0.00393969 | -0.00582872 | 0.00976841 | 0.0825663 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0772247 | 0.00910587 | -0.00398883 | 0.0130947 | 0.0582087 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Classification — xgboost

| Horizon | Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.613958 | 0.500084 | 0.346837 | 0.000337384 | 0.000674033 | 0.559646 | 0.433497 | 0.661731 | 0.234621 |
| 5 | 854661 | 0.565417 | 0.50922 | 0.629636 | 0.0336188 | 0.0623391 | 0.558922 | 0.495377 | 0.681175 | 0.24408 |
| 10 | 821872 | 0.557519 | 0.514019 | 0.608547 | 0.055159 | 0.0968315 | 0.555639 | 0.505215 | 0.684032 | 0.245495 |
| 20 | 758744 | 0.546433 | 0.519913 | 0.553915 | 0.125244 | 0.194662 | 0.553085 | 0.512516 | 0.686154 | 0.246551 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.101111 | -0.00141572 | -0.0068829 | 0.00546718 | 0.0884838 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.111661 | 0.00160633 | -0.0082678 | 0.00987413 | 0.098406 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.105284 | 0.00412205 | -0.00805788 | 0.0121799 | 0.0944014 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0981209 | 0.0100828 | -0.00756446 | 0.0176473 | 0.07379 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Regression — catboost

| Horizon | Scored OOS | mae | rmse | r2 | spearman |
| --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.0191649 | 0.0275636 | 0.0049745 | 0.0875539 |
| 5 | 854661 | 0.0464405 | 0.0659511 | 0.00194716 | 0.0652365 |
| 10 | 821872 | 0.0660484 | 0.0933414 | -0.00232985 | 0.0512922 |
| 20 | 758744 | 0.0927873 | 0.131629 | -0.0102206 | 0.0534811 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0843921 | -0.00169124 | -0.0065482 | 0.00485696 | 0.0782859 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.076021 | 0.00236989 | -0.00720086 | 0.00957075 | 0.0692076 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.0850203 | 0.00650238 | -0.00809548 | 0.0145979 | 0.0621068 | 2 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0968325 | 0.0177083 | -0.00970617 | 0.0274145 | 0.070748 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Regression — hist_gradient_boosting

| Horizon | Scored OOS | mae | rmse | r2 | spearman |
| --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.0191599 | 0.0275498 | 0.00595835 | 0.091078 |
| 5 | 854661 | 0.0464287 | 0.0659313 | 0.00253838 | 0.0626999 |
| 10 | 821872 | 0.0660299 | 0.0933065 | -0.00154444 | 0.0567996 |
| 20 | 758744 | 0.0927915 | 0.131594 | -0.00962011 | 0.0484901 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0871925 | -0.00153677 | -0.00648358 | 0.00494682 | 0.0779876 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.0798334 | 0.00273315 | -0.00733388 | 0.010067 | 0.0734013 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.088891 | 0.00790136 | -0.00853078 | 0.0164321 | 0.0680547 | 2 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0911941 | 0.0197232 | -0.00981599 | 0.0295392 | 0.066805 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Regression — lightgbm

| Horizon | Scored OOS | mae | rmse | r2 | spearman |
| --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.0191624 | 0.0275524 | 0.00577591 | 0.0898589 |
| 5 | 854661 | 0.0464282 | 0.0659259 | 0.00269786 | 0.0623084 |
| 10 | 821872 | 0.0660445 | 0.09333 | -0.00205457 | 0.0533629 |
| 20 | 758744 | 0.0927518 | 0.131558 | -0.00909117 | 0.0516623 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0853193 | -0.00160274 | -0.00645628 | 0.00485354 | 0.0749589 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.0789353 | 0.00284036 | -0.00733817 | 0.0101785 | 0.0728962 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.0856937 | 0.00703522 | -0.00830233 | 0.0153376 | 0.0675495 | 2 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0931646 | 0.0196001 | -0.00986411 | 0.0294642 | 0.0701429 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Regression — random_forest

| Horizon | Scored OOS | mae | rmse | r2 | spearman |
| --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.019184 | 0.0275849 | 0.00346522 | 0.0723452 |
| 5 | 854661 | 0.0464755 | 0.0660073 | 0.000252059 | 0.0369664 |
| 10 | 821872 | 0.0661222 | 0.0934224 | -0.00404263 | 0.0373793 |
| 20 | 758744 | 0.0930699 | 0.131941 | -0.0149714 | 0.0375569 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0759007 | -0.00231067 | -0.00660259 | 0.00429192 | 0.0640045 | 2 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.0505609 | 0.000538466 | -0.00498617 | 0.00552464 | 0.0293049 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.0716861 | 0.00658415 | -0.00645639 | 0.0130405 | 0.0558525 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0670714 | 0.0136893 | -0.00625809 | 0.0199474 | 0.0529277 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Regression — ridge

| Horizon | Scored OOS | mae | rmse | r2 | spearman |
| --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.0192287 | 0.0276367 | -0.000300074 | 0.0389746 |
| 5 | 854661 | 0.0466367 | 0.0661695 | -0.0046742 | 0.0249675 |
| 10 | 821872 | 0.0662733 | 0.0936227 | -0.00848576 | 0.0388571 |
| 20 | 758744 | 0.0931661 | 0.132034 | -0.0166578 | 0.0501667 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0410819 | -0.0027695 | -0.0053992 | 0.0026297 | 0.0350356 | 0 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.0499996 | 0.000366327 | -0.00564813 | 0.00601445 | 0.0382461 | 0 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.0626419 | 0.00477074 | -0.00604174 | 0.0108125 | 0.0454253 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0765948 | 0.0146884 | -0.0062137 | 0.0209021 | 0.0466651 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Regression — xgboost

| Horizon | Scored OOS | mae | rmse | r2 | spearman |
| --- | --- | --- | --- | --- | --- |
| 1 | 881455 | 0.0191588 | 0.0275478 | 0.00609397 | 0.0913332 |
| 5 | 854661 | 0.0464142 | 0.0659034 | 0.0033726 | 0.0679873 |
| 10 | 821872 | 0.0660263 | 0.0933062 | -0.00152934 | 0.0550987 |
| 20 | 758744 | 0.0927638 | 0.131563 | -0.00918183 | 0.0498261 |

| Horizon | Rank IC | Top quintile | Bottom quintile | Top-minus-bottom | Worst fold IC | Folds beating naive | LOW cost return | STRESS return | Research status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0870037 | -0.00160041 | -0.00653186 | 0.00493145 | 0.0791063 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 5 | 0.0808156 | 0.00316366 | -0.00741254 | 0.0105762 | 0.0776156 | 3 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 10 | 0.0867255 | 0.00754563 | -0.00841564 | 0.0159613 | 0.0678507 | 2 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |
| 20 | 0.0905446 | 0.0195274 | -0.00954723 | 0.0290746 | 0.0697298 | 1 / 3 | UNAVAILABLE | UNAVAILABLE | REAL_RESEARCH_INSUFFICIENT_EVIDENCE |

## Selected candidates: confirmation and final holdout

Only the four development-locked candidates were evaluated in 2025 and
2026. Other families have no 2026 result; they were not refitted or scored
on the final holdout. No retuning follows final-holdout results.

### 2025 confirmation

**1-session classification / hist_gradient_boosting**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 463967 | 0.596601 | 0.500093 | 0.589286 | 0.000352594 | 0.000704767 | 0.548703 | 0.441259 | 0.670309 | 0.238781 | 0.0927873 | 0.00518725 | True |

**5-session classification / hist_gradient_boosting**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 449480 | 0.58694 | 0.515292 | 0.560548 | 0.0705386 | 0.125309 | 0.553609 | 0.472877 | 0.676616 | 0.241807 | 0.114104 | 0.0114057 | True |

**10-session classification / xgboost**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 431506 | 0.577026 | 0.50668 | 0.450022 | 0.0977625 | 0.16063 | 0.526588 | 0.434172 | 0.680577 | 0.243762 | 0.107554 | 0.0141186 | False |

**20-session classification / hist_gradient_boosting**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 396136 | 0.570266 | 0.513525 | 0.459324 | 0.171417 | 0.249662 | 0.506967 | 0.43787 | 0.685256 | 0.246062 | 0.108482 | 0.0211745 | False |

### 2026 final holdout

**1-session classification / hist_gradient_boosting**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 363765 | 0.586838 | 0.500046 | 0.490385 | 0.000339339 | 0.00067821 | 0.545701 | 0.447587 | 0.674184 | 0.240702 | 0.0927998 | 0.00556758 | True |

**5-session classification / hist_gradient_boosting**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 349367 | 0.576234 | 0.506469 | 0.497196 | 0.0503359 | 0.0914168 | 0.542426 | 0.45573 | 0.67814 | 0.242588 | 0.110397 | 0.0116968 | True |

**10-session classification / xgboost**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 331528 | 0.570775 | 0.509406 | 0.564935 | 0.0458847 | 0.0848757 | 0.551047 | 0.478356 | 0.679643 | 0.243334 | 0.125718 | 0.0205477 | True |

**20-session classification / hist_gradient_boosting**

| Scored OOS | accuracy | balanced_accuracy | precision | recall | f1 | roc_auc | pr_auc_average_precision | log_loss | brier_score | Rank IC | Top-minus-bottom | Beats naive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 298663 | 0.558211 | 0.523805 | 0.6809 | 0.0795183 | 0.142406 | 0.570191 | 0.537958 | 0.682296 | 0.244651 | 0.130842 | 0.0329754 | True |

Incomplete identities, research instrument classification, missing sessions,
unadjusted corporate actions and final-vintage revision timing limit these
results. Unresolved holdings keep full-path return metrics unavailable;
closed-trade statistics cannot establish an entire strategy's profitability.
Benchmark and PIT fundamentals remain UNAVAILABLE. The fixed baseline arena
is not an optimized configuration. Logistic convergence diagnostics are in
real-model-fit-diagnostics.json. P11–P14 are unchanged; P17 is not started.
