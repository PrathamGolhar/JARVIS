import { Citation } from "../api/chat";

type CitationsListProps = {
  citations: Citation[];
};

export function CitationsList({ citations }: CitationsListProps) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="citations-container" aria-label="Verified Source References">
      <p className="citations-header">VERIFIED SOURCES</p>
      <div className="citations-grid">
        {citations.map((cite, index) => (
          <a
            key={`${cite.url}-${index}`}
            href={cite.url}
            target="_blank"
            rel="noopener noreferrer"
            className="citation-link"
            title={cite.title}
          >
            <span className="citation-badge">[{index + 1}]</span>
            <span className="citation-title">{cite.title}</span>
            {cite.domain && <small className="citation-domain">({cite.domain})</small>}
          </a>
        ))}
      </div>
    </div>
  );
}
