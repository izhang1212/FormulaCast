# FormulaCast

## Overview

**Description:** This project is an F1 race outcome simulator that generates probabilistic forcast for Formula 1 Grand Prix results

**Method:** Using a Random Forest model that is trained on race data and a Monte Carlo engine that then runs simluated races on top of that baseline

**Goal:** To find a full probabilty distirubtion for every competing driver's finishing position 

**Set Up Instructions:** Use update_season.py to download all seasons from 2018-2026. Once done, run main and test.

## Deployment

FormulaCast is deployed as a split app:

- Vercel hosts the Vite frontend.
- Render hosts the FastAPI backend and runs the model refresh.
- Supabase Storage stores season/race CSV inputs.


## Prediction Strategies Implemented:
- **Random Forest Regression:**  Walk-forward validated model predicting finishing positions from 20+ engineered features, with exponentially weighted rolling averages to capture recent form
- **Monte Carlo Simulation** — 20,000 lap-by-lap races per Grand Prix, starting from the real grid:
  - Each driver's race pace is the Random Forest's predicted position plus race-day noise (tighter for front-runners)
  - Lap-by-lap overtakes between adjacent cars, more likely the bigger the pace gap, scaled by each circuit's historical overtaking
  - Safety car periods (first-lap multiplier, no passing under SC, shuffled restarts) and a chaotic lap-1 start
  - DNF probability blended from track, driver and team history; retirements classified by laps completed
  - Mid-race incidents (spins, slow stops, penalties) that cost a few places
  - Parameters tuned on walk-forward backtests (2019–2023) and checked on 2024–2026

### Backend Example Output:
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

- [Monte-Carlo](https://en.wikipedia.org/wiki/Monte_Carlo_method)

- [Random-Forest](https://en.wikipedia.org/wiki/Random_forest)
