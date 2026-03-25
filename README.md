# FormulaCast

## Overview

**Description:** This project is an F1 race outcome simulator that generates probabilistic forcast for Formula 1 Grand Prix results

**Method:** Using a Random Forest model that is trained on race data and a Monte Carlo engine that then runs simluated races on top of that baseline

**Goal:** To find a full probabilty distirubtion for every competing driver's finishing position 

## Strategies Implemented:
- **Random Forest Regression:**  Walk-forward validated model predicting finishing positions from 20+ engineered features, with exponentially weighted rolling averages to capture recent form
- **Monte Carlo Simulation** — 10,000 race iterations with stochastic event modeling:
  - Safety car probability per lap (with first-lap multiplier and cooldown)
  - Mechanical DNF rates per constructor
  - Pit stop time variance and botched stop probability
  - Lap-by-lap overtake attempts based on pace differentials

### Example Output:
```
--- Monte Carlo Results ---
Simulations: 10000

Driver   E[Pos]  Win%  Podium%  Points%  E[Pts]
--------------------------------------------------
VER        2.1   42.3%   81.5%    97.2%   19.84
NOR        3.4   18.7%   58.3%    93.1%   14.22
LEC        4.2   12.1%   44.7%    89.5%   11.67
PIA        5.8    6.3%   25.4%    82.0%    8.93
HAM        6.1    5.2%   22.1%    78.4%    8.12
...
```

## APIs
FormulaCast uses real historical data from the offical F1 timing API via Fastf1

## References:

- ![Monte-Carlo](https://en.wikipedia.org/wiki/Monte_Carlo_method)

- ![Random-Forest](https://en.wikipedia.org/wiki/Random_forest)

