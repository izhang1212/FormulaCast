// All static lookup data lives here so views/components stay logic-only.

export const NAME = {
  HAM:'Hamilton',BOT:'Bottas',VET:'Vettel',RAI:'Raikkonen',VER:'Verstappen',
  RIC:'Ricciardo',HUL:'Hulkenberg',SAI:'Sainz',PER:'Perez',OCO:'Ocon',
  ALO:'Alonso',VAN:'Vandoorne',GAS:'Gasly',HAR:'Hartley',MAG:'Magnussen',
  GRO:'Grosjean',LEC:'Leclerc',ERI:'Ericsson',STR:'Stroll',SIR:'Sirotkin',
  ALB:'Albon',NOR:'Norris',GIO:'Giovinazzi',KVY:'Kvyat',RUS:'Russell',
  KUB:'Kubica',LAT:'Latifi',TSU:'Tsunoda',MAZ:'Mazepin',MSC:'Schumacher',
  ZHO:'Zhou',SAR:'Sargeant',LAW:'Lawson',PIA:'Piastri',ANT:'Antonelli',
  BEA:'Bearman',HAD:'Hadjar',BOR:'Bortoleto',LIN:'Lindblad',COL:'Colapinto',
};

export const TEAMC = {
  MER:'#27F4D2',RED:'#3671C6',FER:'#E8002D',McL:'#FF8000',AST:'#229971',
  ALP:'#0093CC',WIL:'#64C4FF',RB:'#6692FF',AT:'#2B4562',TR:'#2B4562',
  SAU:'#52E252',ALF:'#900000',REN:'#FFD800',FI:'#F596C8',RP:'#F596C8',
  HAA:'#B6BABD',CAD:'#B89B5E',AUD:'#BB0A30',
};

export const TRACK = {
  catalunya:"M30,90 C20,60 35,40 60,38 C85,36 95,55 120,52 C150,48 165,30 175,45 C185,60 160,68 150,80 C140,92 110,86 90,92 C70,98 45,104 30,90 Z",
  redbull:"M40,80 C30,55 50,38 80,40 C120,43 140,30 165,42 C180,50 170,66 150,70 C120,76 110,92 80,90 C55,88 48,92 40,80 Z",
  suzuka:"M40,55 C55,30 95,32 105,55 C112,72 95,80 78,72 C70,68 72,58 82,58 C150,58 175,75 160,92 C145,105 110,98 95,86 C70,66 25,80 40,55 Z",
  monaco:"M35,75 C30,55 45,48 60,52 C70,55 68,68 80,66 C92,64 88,46 105,44 C125,42 130,58 150,56 C168,54 172,72 158,82 C140,94 120,82 100,88 C78,95 42,96 35,75 Z",
  silverstone:"M30,70 C25,48 45,38 75,42 C115,47 130,32 160,44 C182,53 178,72 158,78 C125,88 130,96 95,94 C60,92 40,90 30,70 Z",
  melbourne:"M35,80 C25,55 45,40 75,42 C110,45 130,32 160,44 C180,52 175,70 150,74 C120,79 115,95 85,92 C58,89 45,98 35,80 Z",
  shanghai:"M40,85 C30,70 35,50 55,48 C70,46 72,60 85,56 C100,51 92,35 110,33 C135,30 145,52 165,50 C182,48 180,70 162,76 C130,86 120,96 90,93 C65,90 50,98 40,85 Z",
};

// Race name -> circuit outline / location. Names not listed render no outline.
export const TRACK_BY_NAME = {
  "Australian Grand Prix":"melbourne","Chinese Grand Prix":"shanghai",
  "Spanish Grand Prix":"catalunya","Barcelona Grand Prix":"catalunya","Monaco Grand Prix":"monaco",
  "British Grand Prix":"silverstone","Japanese Grand Prix":"suzuka",
  "Austrian Grand Prix":"redbull",
};
export const LOC_BY_NAME = {
  "Australian Grand Prix":"Albert Park · AUS","Chinese Grand Prix":"Shanghai Intl · CHN",
  "Spanish Grand Prix":"Barcelona-Catalunya · ESP","Barcelona Grand Prix":"Circuit de Barcelona-Catalunya · ESP","Monaco Grand Prix":"Circuit de Monaco · MON",
  "British Grand Prix":"Silverstone · GBR","Japanese Grand Prix":"Suzuka · JPN",
  "Austrian Grand Prix":"Red Bull Ring · AUT",
};

// Per-season lineups — used only to color the driver tick by team.
export const ROSTERS = {
  2018:[["HAM","MER"],["BOT","MER"],["VET","FER"],["RAI","FER"],["VER","RED"],["RIC","RED"],["HUL","REN"],["SAI","REN"],["PER","FI"],["OCO","FI"],["ALO","McL"],["VAN","McL"],["GAS","TR"],["HAR","TR"],["MAG","HAA"],["GRO","HAA"],["LEC","SAU"],["ERI","SAU"],["STR","WIL"],["SIR","WIL"]],
  2019:[["HAM","MER"],["BOT","MER"],["VER","RED"],["LEC","FER"],["VET","FER"],["ALB","RED"],["SAI","McL"],["NOR","McL"],["RIC","REN"],["HUL","REN"],["PER","RP"],["STR","RP"],["GAS","TR"],["KVY","TR"],["RAI","ALF"],["GIO","ALF"],["MAG","HAA"],["GRO","HAA"],["RUS","WIL"],["KUB","WIL"]],
  2020:[["HAM","MER"],["BOT","MER"],["VER","RED"],["ALB","RED"],["LEC","FER"],["VET","FER"],["NOR","McL"],["SAI","McL"],["PER","RP"],["STR","RP"],["RIC","REN"],["OCO","REN"],["GAS","AT"],["KVY","AT"],["RAI","ALF"],["GIO","ALF"],["MAG","HAA"],["GRO","HAA"],["RUS","WIL"],["LAT","WIL"]],
  2021:[["VER","RED"],["PER","RED"],["HAM","MER"],["BOT","MER"],["NOR","McL"],["RIC","McL"],["LEC","FER"],["SAI","FER"],["GAS","AT"],["TSU","AT"],["ALO","ALP"],["OCO","ALP"],["VET","AST"],["STR","AST"],["RAI","ALF"],["GIO","ALF"],["RUS","WIL"],["LAT","WIL"],["MSC","HAA"],["MAZ","HAA"]],
  2022:[["VER","RED"],["PER","RED"],["LEC","FER"],["SAI","FER"],["HAM","MER"],["RUS","MER"],["NOR","McL"],["RIC","McL"],["ALO","ALP"],["OCO","ALP"],["GAS","AT"],["TSU","AT"],["VET","AST"],["STR","AST"],["BOT","ALF"],["ZHO","ALF"],["MAG","HAA"],["MSC","HAA"],["ALB","WIL"],["LAT","WIL"]],
  2023:[["VER","RED"],["PER","RED"],["HAM","MER"],["RUS","MER"],["ALO","AST"],["STR","AST"],["LEC","FER"],["SAI","FER"],["NOR","McL"],["PIA","McL"],["GAS","ALP"],["OCO","ALP"],["BOT","ALF"],["ZHO","ALF"],["TSU","AT"],["RIC","AT"],["HUL","HAA"],["MAG","HAA"],["ALB","WIL"],["SAR","WIL"]],
  2024:[["VER","RED"],["PER","RED"],["HAM","MER"],["RUS","MER"],["LEC","FER"],["SAI","FER"],["NOR","McL"],["PIA","McL"],["ALO","AST"],["STR","AST"],["GAS","ALP"],["OCO","ALP"],["TSU","RB"],["RIC","RB"],["BOT","SAU"],["ZHO","SAU"],["HUL","HAA"],["MAG","HAA"],["ALB","WIL"],["COL","WIL"]],
  2025:[["NOR","McL"],["PIA","McL"],["VER","RED"],["TSU","RED"],["LEC","FER"],["HAM","FER"],["RUS","MER"],["ANT","MER"],["ALO","AST"],["STR","AST"],["GAS","ALP"],["COL","ALP"],["ALB","WIL"],["SAI","WIL"],["OCO","HAA"],["BEA","HAA"],["HAD","RB"],["LAW","RB"],["HUL","SAU"],["BOR","SAU"]],
  2026:[["NOR","McL"],["PIA","McL"],["ANT","MER"],["RUS","MER"],["VER","RED"],["LIN","RED"],["LEC","FER"],["HAM","FER"],["ALO","AST"],["STR","AST"],["GAS","ALP"],["COL","ALP"],["ALB","WIL"],["SAI","WIL"],["OCO","HAA"],["BEA","HAA"],["HAD","RB"],["LAW","RB"],["HUL","AUD"],["BOR","AUD"],["PER","CAD"],["BOT","CAD"]],
};

export const STEPS = [
  {k:'01 · Ingest',t:'Data',d:'Every race weekend since 2018 is pulled from the FastF1 API — results, qualifying, lap times, weather, and free-practice pace. Each season is cached as its own file so the dataset grows race by race.'},
  {k:'02 · Transform',t:'Feature Engineering',d:'Raw results become signals the model can learn from: rolling and exponentially-weighted form, team strength, grid-to-finish history, circuit experience and qualifying gaps — each computed only from a driver\u2019s prior races, never the future.'},
  {k:'03 · Learn',t:'Random Forest',d:'A Random Forest learns how far each driver tends to move from their grid slot, predicting a residual — positions gained or lost. Added to the starting grid, that gives an expected finishing position. Trained on past seasons, tested walk-forward on the next.'},
  {k:'04 · Anchor',t:'The Grid',d:'A finish prediction needs a start. After qualifying, the real penalty-adjusted grid is used. Before qualifying, FormulaCast samples a plausible grid from current form — so an upcoming race can be forecast days ahead.'},
  {k:'05 · Simulate',t:'Monte Carlo',d:'The expected order is only the average case. The Monte Carlo engine runs the race ten thousand times, injecting safety cars, first-lap incidents, mechanical DNFs, pit-stop variance and lap-by-lap overtaking — with event rates calibrated per circuit.'},
  {k:'06 · Aggregate',t:'Probabilities',d:'Across ten thousand simulated races, the spread of where each driver lands becomes the output: win probability, podium and points odds, expected position, and the full finishing distribution.'},
];

// driver -> team color for a given season
export function teamColor(year, driver) {
  const roster = ROSTERS[year];
  const found = roster && roster.find(([ab]) => ab === driver);
  return (found && TEAMC[found[1]]) || 'var(--grey-2)';
}

// attach display metadata (track outline, location) to a fetched race
export function withMeta(race) {
  return {
    ...race,
    track: TRACK_BY_NAME[race.name] || null,
    loc: LOC_BY_NAME[race.name] || `Round ${race.round} · ${race.year}`,
  };
}
