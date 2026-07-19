import { AlertTriangle, CloudLightning } from "lucide-react";
import type { DocumentaryState, RegionResult } from "../types";

const markerClass: Record<DocumentaryState, string> = {
  strong: "marker marker-strong",
  low: "marker marker-low",
  validation: "marker marker-validation",
  mixed: "marker marker-mixed",
  insufficient: "marker marker-insufficient",
  unavailable: "marker marker-unavailable",
};

interface IndiaMapProps {
  regions: RegionResult[];
  selectedId: string;
  crisisEnabled: boolean;
  onSelect: (region: RegionResult) => void;
}

export function IndiaMap({ regions, selectedId, crisisEnabled, onSelect }: IndiaMapProps) {
  return (
    <section className="map-panel" aria-label="Planner map">
      <div className="map-toolbar">
        <div>
          <span className="eyebrow">Local geometry</span>
          <strong>India documentary evidence map</strong>
        </div>
        <div className="map-meta">
          {crisisEnabled ? (
            <span className="status-pill status-warning">
              <CloudLightning size={14} aria-hidden="true" />
              Demo flood overlay
            </span>
          ) : (
            <span className="status-pill">No external tiles</span>
          )}
        </div>
      </div>
      <div className="map-canvas">
        <svg
          viewBox="0 0 100 100"
          role="img"
          aria-labelledby="india-map-title india-map-description"
          className="india-map"
        >
          <title id="india-map-title">India planning results</title>
          <desc id="india-map-description">
            Local schematic outline of India with selectable postal reference results. Use the
            synchronized table for a complete non-map alternative.
          </desc>
          <defs>
            <pattern id="stipple" width="4" height="4" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r=".55" fill="currentColor" />
            </pattern>
            <pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
              <line x1="0" y1="0" x2="0" y2="5" stroke="currentColor" strokeWidth="1.2" />
            </pattern>
            <filter id="marker-shadow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="1" stdDeviation="1.1" floodOpacity=".28" />
            </filter>
          </defs>
          <path
            className="india-outline"
            d="M31 8 L39 10 L45 8 L51 12 L58 10 L64 16 L70 18 L74 25 L82 27 L89 33 L86 38 L80 41 L77 49 L70 53 L68 61 L63 66 L59 76 L54 89 L48 82 L44 72 L38 67 L35 59 L29 56 L26 48 L20 43 L18 35 L22 28 L25 19 Z"
          />
          <path className="map-border-line" d="M25 35 C40 31 52 33 73 28" />
          <path className="map-border-line" d="M29 55 C42 47 58 50 72 43" />
          <path className="map-border-line" d="M40 68 C50 60 61 61 66 58" />
          {crisisEnabled && (
            <g className="crisis-area" aria-label="Demo flood affected area">
              <path d="M51 33 C59 27 73 29 79 36 C72 42 62 45 52 42 Z" />
              <AlertTriangle x="64" y="33" width="5" height="5" />
            </g>
          )}
          {regions.map((region) => (
            <g
              key={region.id}
              className={`${markerClass[region.documentaryState]} ${
                region.id === selectedId ? "is-selected" : ""
              }`}
              transform={`translate(${region.x} ${region.y})`}
              role="button"
              tabIndex={0}
              aria-label={`${region.name}: ${region.documentaryLabel}`}
              onClick={() => onSelect(region)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect(region);
                }
              }}
            >
              <circle r="4.6" className="marker-ring" />
              <circle r="3.1" className="marker-core" filter="url(#marker-shadow)" />
              {region.documentaryState === "validation" && (
                <circle r="2.4" fill="url(#hatch)" className="marker-pattern" />
              )}
              {region.documentaryState === "insufficient" && (
                <circle r="2.4" fill="url(#stipple)" className="marker-pattern" />
              )}
            </g>
          ))}
        </svg>
        <div className="map-annotation">
          <span>Postal reference points</span>
          <strong>Not PIN centroids or population origins</strong>
        </div>
      </div>
      <div className="legend" aria-label="Map legend">
        <span><i className="legend-dot strong" />Strong support</span>
        <span><i className="legend-dot low" />Low support</span>
        <span><i className="legend-dot validation" />Validation required</span>
        <span><i className="legend-dot mixed" />Mixed evidence</span>
        <span><i className="legend-dot insufficient" />Insufficient corpus</span>
        <span><i className="legend-dot unavailable" />Unavailable</span>
      </div>
    </section>
  );
}
