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
  miami:"M35,72 C45,42 82,38 108,47 C132,55 155,38 170,52 C184,66 160,80 138,76 C110,70 92,92 62,88 C42,85 28,88 35,72 Z",
  bahrain:"M45,82 C25,62 35,36 65,34 C92,32 100,56 120,50 C145,44 166,52 168,70 C170,90 132,82 118,96 C100,112 70,100 72,82 C74,62 52,98 45,82 Z",
  jeddah:"M28,88 C58,58 70,22 104,30 C136,38 118,72 152,66 C174,62 182,84 160,94 C126,110 104,78 78,92 C54,104 38,104 28,88 Z",
  imola:"M38,78 C28,54 50,34 82,38 C112,42 116,24 146,34 C174,44 170,74 148,78 C126,82 116,100 88,94 C58,88 48,94 38,78 Z",
  spa:"M28,74 C32,40 62,32 84,48 C108,66 118,32 146,42 C174,52 172,82 148,90 C118,102 88,78 64,88 C42,98 24,94 28,74 Z",
  zandvoort:"M42,86 C22,70 30,42 58,34 C82,28 98,50 116,42 C144,30 176,48 172,70 C168,94 136,96 112,84 C86,72 64,102 42,86 Z",
  monza:"M32,88 C28,48 56,36 86,42 C112,48 124,32 156,42 C184,52 176,82 148,82 C116,82 104,98 74,92 C50,88 36,104 32,88 Z",
  marinaBay:"M35,84 C28,58 48,52 64,62 C76,72 86,52 102,56 C120,60 116,36 140,34 C166,32 180,54 164,68 C148,82 126,72 114,92 C102,112 72,96 58,88 C48,82 42,94 35,84 Z",
  cota:"M26,74 C34,40 68,34 86,54 C102,72 120,50 144,54 C168,58 180,80 160,90 C134,102 112,82 90,92 C62,106 34,100 26,74 Z",
  mexico:"M34,74 C24,48 48,36 76,42 C106,48 104,66 130,62 C158,58 176,72 164,90 C148,108 116,88 92,94 C62,102 42,98 34,74 Z",
  interlagos:"M44,84 C28,70 34,46 58,44 C84,42 90,62 112,56 C138,48 172,50 168,74 C164,98 124,88 106,96 C82,108 54,104 44,84 Z",
  lasVegas:"M30,82 L86,82 C104,82 112,68 102,56 L80,34 C72,26 86,18 98,26 L168,74 C182,84 170,100 154,92 L118,74 C104,66 98,98 70,96 C48,94 34,96 30,82 Z",
  lusail:"M40,84 C22,58 44,36 76,38 C108,40 116,24 148,34 C174,42 180,66 160,78 C132,94 112,78 90,90 C66,102 48,100 40,84 Z",
  yasMarina:"M36,82 C24,58 42,40 72,42 C96,44 104,60 126,52 C156,40 178,58 166,78 C154,98 126,90 106,100 C82,112 48,102 36,82 Z",
  baku:"M26,78 L60,78 L60,42 C60,28 82,28 82,44 L82,70 L124,70 C148,70 146,38 166,38 C184,38 184,66 164,76 L120,96 L54,96 C34,96 26,90 26,78 Z",
  montreal:"M38,78 C26,54 48,36 80,40 C110,44 112,62 136,58 C164,54 178,70 166,88 C150,108 118,86 92,96 C66,106 46,100 38,78 Z",
  hungaroring:"M42,82 C24,64 36,38 68,36 C94,34 104,52 126,46 C154,38 178,56 168,76 C156,100 124,86 104,96 C78,110 52,100 42,82 Z",
  paulRicard:"M30,76 C34,50 62,42 88,50 C112,58 124,36 154,42 C178,46 180,68 162,78 C140,90 126,74 106,88 C78,106 46,102 30,76 Z",
  hockenheim:"M36,80 C30,52 56,36 86,42 C120,48 128,34 158,42 C182,50 174,82 146,82 C120,82 110,98 82,94 C56,90 42,100 36,80 Z",
  portimao:"M34,78 C24,54 44,34 74,38 C100,42 110,58 132,48 C158,36 180,52 168,74 C154,100 122,82 100,94 C72,110 44,100 34,78 Z",
  istanbul:"M32,74 C28,48 54,34 82,42 C110,50 120,30 150,40 C176,48 178,74 154,82 C124,92 110,72 90,90 C66,112 38,100 32,74 Z",
  mugello:"M36,76 C26,50 52,34 82,40 C108,46 122,32 150,44 C176,56 168,84 144,86 C118,88 102,104 76,96 C54,90 42,98 36,76 Z",
  sochi:"M30,78 C28,50 56,38 86,42 C122,48 138,34 164,48 C184,58 174,86 146,84 L68,84 C48,84 34,94 30,78 Z",
};

// Race name -> circuit outline / location. Names not listed render no outline.
export const TRACK_BY_NAME = {
  "Australian Grand Prix":"melbourne","Chinese Grand Prix":"shanghai",
  "Spanish Grand Prix":"catalunya","Barcelona Grand Prix":"catalunya","Monaco Grand Prix":"monaco",
  "British Grand Prix":"silverstone","Japanese Grand Prix":"suzuka",
  "Austrian Grand Prix":"redbull","Styrian Grand Prix":"redbull",
  "Miami Grand Prix":"miami","Bahrain Grand Prix":"bahrain","Sakhir Grand Prix":"bahrain",
  "Saudi Arabian Grand Prix":"jeddah","Emilia Romagna Grand Prix":"imola",
  "Belgian Grand Prix":"spa","Dutch Grand Prix":"zandvoort","Italian Grand Prix":"monza",
  "Singapore Grand Prix":"marinaBay","United States Grand Prix":"cota",
  "Mexico City Grand Prix":"mexico","Mexican Grand Prix":"mexico","São Paulo Grand Prix":"interlagos",
  "Brazilian Grand Prix":"interlagos","Las Vegas Grand Prix":"lasVegas",
  "Qatar Grand Prix":"lusail","Abu Dhabi Grand Prix":"yasMarina",
  "Azerbaijan Grand Prix":"baku","Canadian Grand Prix":"montreal",
  "Hungarian Grand Prix":"hungaroring","French Grand Prix":"paulRicard",
  "German Grand Prix":"hockenheim","Eifel Grand Prix":"hockenheim",
  "Portuguese Grand Prix":"portimao","Turkish Grand Prix":"istanbul",
  "Tuscan Grand Prix":"mugello","Russian Grand Prix":"sochi",
  "70th Anniversary Grand Prix":"silverstone",
};
export const LOC_BY_NAME = {
  "Australian Grand Prix":"Albert Park · AUS","Chinese Grand Prix":"Shanghai Intl · CHN",
  "Spanish Grand Prix":"Barcelona-Catalunya · ESP","Barcelona Grand Prix":"Circuit de Barcelona-Catalunya · ESP","Monaco Grand Prix":"Circuit de Monaco · MON",
  "British Grand Prix":"Silverstone · GBR","Japanese Grand Prix":"Suzuka · JPN",
  "Austrian Grand Prix":"Red Bull Ring · AUT",
  "Styrian Grand Prix":"Red Bull Ring · AUT","Miami Grand Prix":"Miami Intl Autodrome · USA",
  "Bahrain Grand Prix":"Bahrain Intl Circuit · BHR","Sakhir Grand Prix":"Bahrain Outer Track · BHR",
  "Saudi Arabian Grand Prix":"Jeddah Corniche · SAU","Emilia Romagna Grand Prix":"Imola · ITA",
  "Belgian Grand Prix":"Spa-Francorchamps · BEL","Dutch Grand Prix":"Zandvoort · NED",
  "Italian Grand Prix":"Monza · ITA","Singapore Grand Prix":"Marina Bay · SGP",
  "United States Grand Prix":"Circuit of the Americas · USA",
  "Mexico City Grand Prix":"Autodromo Hermanos Rodriguez · MEX","Mexican Grand Prix":"Autodromo Hermanos Rodriguez · MEX",
  "São Paulo Grand Prix":"Interlagos · BRA","Brazilian Grand Prix":"Interlagos · BRA",
  "Las Vegas Grand Prix":"Las Vegas Strip Circuit · USA","Qatar Grand Prix":"Lusail · QAT",
  "Abu Dhabi Grand Prix":"Yas Marina · UAE","Azerbaijan Grand Prix":"Baku City Circuit · AZE",
  "Canadian Grand Prix":"Circuit Gilles Villeneuve · CAN","Hungarian Grand Prix":"Hungaroring · HUN",
  "French Grand Prix":"Paul Ricard · FRA","German Grand Prix":"Hockenheimring · GER",
  "Eifel Grand Prix":"Nurburgring · GER","Portuguese Grand Prix":"Portimao · POR",
  "Turkish Grand Prix":"Istanbul Park · TUR","Tuscan Grand Prix":"Mugello · ITA",
  "Russian Grand Prix":"Sochi Autodrom · RUS","70th Anniversary Grand Prix":"Silverstone · GBR",
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
