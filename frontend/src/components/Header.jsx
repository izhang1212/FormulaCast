const NAV = [
  { id: "home", label: "Home" },
  { id: "about", label: "About" },
  { id: "predict", label: "Predict" },
  { id: "replay", label: "Replay" },
  { id: "performance", label: "Performance" },
];

export default function Header({ view, onNavigate }) {
  return (
    <header>
      <div className="brand" onClick={() => onNavigate("home")}>
        <div className="bars"><i /><i /><i /></div>
        <div className="name">Formula<b>Cast</b></div>
      </div>
      <nav>
        {NAV.map(n => (
          <button key={n.id} className={`navbtn ${view === n.id ? "active" : ""}`}
                  onClick={() => onNavigate(n.id)}>{n.label}</button>
        ))}
      </nav>
    </header>
  );
}
