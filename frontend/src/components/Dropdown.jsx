import { useState, useRef, useEffect } from "react";

export default function Dropdown({ options, value, onChange }) {
    const [open, setOpen] = useState(false);
    const [hl, setHl] = useState(0);
    const ref = useRef(null);

    useEffect(() => {
        const onDoc = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
        document.addEventListener("click", onDoc);
        return () => document.removeEventListener("click", onDoc);
    }, []);

    const pick = (i) => { onChange(options[i]); setOpen(false); };
    const onKey = (e) => {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            if (!open) setOpen(true);
            else setHl(h => (h + (e.key === "ArrowDown" ? 1 : options.length - 1)) % options.length);
        } else if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            if (open) pick(hl); else { setOpen(true); setHl(Math.max(0, options.indexOf(value))); }
        } else if (e.key === "Escape") setOpen(false);
    };

    return (
        <div className={`dd ${open ? "open" : ""}`} ref={ref}>
            <button className="dd-btn" aria-haspopup="listbox" aria-expanded={open} onKeyDown={onKey}
                onClick={() => { setOpen(o => !o); setHl(Math.max(0, options.indexOf(value))); }}>
                <span className="dd-label">{value}</span><span className="chev" />
            </button>
            <div className="dd-panel" role="listbox">
                {options.map((o, i) => (
                    <div key={o} role="option"
                        className={`dd-opt ${o === value ? "sel" : ""} ${i === hl ? "hl" : ""}`}
                        onMouseEnter={() => setHl(i)} onClick={() => pick(i)}>
                        <span>{o}</span><span className="ck">✓</span>
                    </div>
                ))}
            </div>
        </div>
    );
}