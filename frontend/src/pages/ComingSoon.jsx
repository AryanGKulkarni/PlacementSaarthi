import Icon from '../components/Icon.jsx'

/** Placeholder for pages that haven't been built yet. */
export default function ComingSoon({ title, icon = 'spark' }) {
  return (
    <div className="page">
      <div className="card empty-mini">
        <div className="empty-art">
          <Icon name={icon} size={24} />
        </div>
        <h3>{title}</h3>
        <p>This page is coming soon.</p>
      </div>
    </div>
  )
}
