// Readiness score widgets, shared by the student dashboard and the faculty student drawer.
// Badge colours for readiness.level live in lib/constants.js (LEVEL_TONE).

export function ProgressRing({ score, size = 170 }) {
  const radius = 64
  const circumference = 2 * Math.PI * radius
  return (
    <div
      className="ring-wrap"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Readiness ${score} out of 100`}
    >
      <svg viewBox="0 0 160 160">
        <circle className="ring-track" cx="80" cy="80" r={radius} />
        <circle
          className="ring-value"
          cx="80"
          cy="80"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - score / 100)}
          style={score === 0 ? { opacity: 0 } : undefined} // round caps draw a dot at 0
        />
      </svg>
      <div className="ring-text">
        <strong>{score}</strong>
        <span>/ 100</span>
      </div>
    </div>
  )
}

/** One bar per readiness param (CGPA, skills, backlogs, profile). showDetail adds the backend's explanation. */
export function ReadinessMetrics({ params, showDetail = true }) {
  return (
    <div className="metric-list">
      {params.map((p) => (
        <div className={`metric metric-${p.status}`} key={p.key}>
          <div>
            <span>
              {p.label} <em className="metric-weight">· {p.weight} pts</em>
            </span>
            <strong>{metricValue(p)}</strong>
          </div>
          <div
            className="bar"
            role="progressbar"
            aria-label={p.label}
            aria-valuenow={p.percent}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <i style={{ width: `${p.percent}%` }} />
          </div>
          {showDetail && <small className="metric-detail">{p.detail}</small>}
        </div>
      ))}
    </div>
  )
}

/** Short value on the right of each bar, from the param's meta. */
function metricValue(p) {
  const m = p.meta
  switch (p.key) {
    case 'cgpa':
      return m.value === null ? 'Not added' : `${m.value.toFixed(2)} / 10`
    case 'skills':
      return m.count ? `${m.count} skill${m.count === 1 ? '' : 's'}` : 'Not added'
    case 'backlogs':
      return m.value === 0 ? 'None' : `${m.value} active`
    case 'profile':
      return `${m.filled} / ${m.total}`
    default:
      return `${p.percent}%`
  }
}
