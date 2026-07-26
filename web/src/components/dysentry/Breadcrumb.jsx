import React from "react";
import { Link } from "react-router-dom";

export default function Breadcrumb({ items = [] }) {
  return (
    <nav className="flex items-center gap-2 text-[11px] text-steel" style={{ lineHeight: 1.45 }}>
      {items.map((item, i) => (
        <React.Fragment key={i}>
          {item.path ? (
            <Link to={item.path} className="transition-colors hover:text-ink">{item.label}</Link>
          ) : (
            <span className={i === items.length - 1 ? "text-ink" : ""}>{item.label}</span>
          )}
          {i < items.length - 1 && <span className="text-ash">/</span>}
        </React.Fragment>
      ))}
    </nav>
  );
}