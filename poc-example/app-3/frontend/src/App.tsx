import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  ChartOptions,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'
import './App.css'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
)

type Tab = 'overview' | 'explore' | 'review'

interface Impact {
  business_signal: string
  affected_patient_count: number
  affected_start_rate: number
  comparison_start_rate: number
  start_rate_gap_percentage_points: number
  affected_median_days: number
  comparison_median_days: number
  estimated_excess_starts_at_risk: number
  estimated_incremental_annual_value_at_risk_usd: number
  recommended_action: string
}

interface Cohort {
  cohort: string
  patient_count: number
  treatment_started_count: number
  treatment_abandoned_count: number
  treatment_start_rate: number
  median_days_to_outcome: number
  annual_value_at_risk_usd: number
}

interface Barrier {
  barrier_category: string
  signal_count: number
  average_confidence: number
  review_required_count: number
}

interface AccessTrend {
  prescription_month: string
  patient_count: number
  treatment_start_rate: number
  median_days_to_outcome: number
  annual_value_at_risk_usd: number
}

interface Evidence {
  feedback_id: string
  feedback_timestamp: string
  source: string
  speaker_type: string
  therapy: string
  region: string
  payer_type: string
  barrier_category: string
  barrier_confidence: number
  sentiment: string
  sentiment_confidence: number
  urgency: string
  urgency_confidence: number
  signal_summary: string
  evidence_excerpt: string
  review_required: boolean
}

interface Filters {
  therapies: string[]
  regions: string[]
  payer_types: string[]
  selected: FilterSelection
}

interface FilterSelection {
  therapy: string
  region: string
  payer_type: string
  start_date: string
}

interface DashboardResponse {
  meta: {
    backend: string
    is_snapshot: boolean
    generated_at: string
    disclosure: string
  }
  filters: Filters
  impact: Impact
  cohorts: Cohort[]
  barriers: Barrier[]
  access_trend: AccessTrend[]
  evidence: Evidence[]
  review_required_count: number
}

const initialFilters: FilterSelection = {
  therapy: 'Therapy A',
  region: 'Northeast',
  payer_type: 'Commercial',
  start_date: '2026-05-01',
}

const titleCase = (value: string) =>
  value.replace(/_/g, ' ').replace(/\b\w/g, character => character.toUpperCase())

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)

const formatMonth = (value: string) =>
  new Intl.DateTimeFormat('en-US', { month: 'short' }).format(
    new Date(`${value.slice(0, 10)}T12:00:00`),
  )

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(
    new Date(value),
  )

function Icon({ name }: { name: 'arrow' | 'layers' | 'shield' | 'spark' | 'review' }) {
  const paths = {
    arrow: <path d="M5 12h13m-5-5 5 5-5 5" />,
    layers: <path d="m12 3-8 4 8 4 8-4-8-4Zm-8 9 8 4 8-4M4 17l8 4 8-4" />,
    shield: <path d="M12 3 5 6v5c0 4.6 2.9 8 7 10 4.1-2 7-5.4 7-10V6l-7-3Zm-3 9 2 2 4-4" />,
    spark: <path d="m12 3 1.2 4.8L18 9l-4.8 1.2L12 15l-1.2-4.8L6 9l4.8-1.2L12 3Zm6 11 .7 2.3L21 17l-2.3.7L18 20l-.7-2.3L15 17l2.3-.7L18 14Z" />,
    review: <path d="M5 4h10l4 4v12H5V4Zm9 0v5h5M8 13h8M8 17h5" />,
  }
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
      {paths[name]}
    </svg>
  )
}

function SignalGap({ impact }: { impact: Impact }) {
  return (
    <section className="signal-gap" aria-label="Treatment start rate comparison">
      <div className="signal-gap__header">
        <span className="eyebrow">Treatment-start signal</span>
        <span className="gap-pill">{impact.start_rate_gap_percentage_points.toFixed(1)} point gap</span>
      </div>
      <div className="signal-gap__rail" aria-hidden="true">
        <div
          className="signal-gap__range"
          style={{
            left: `${impact.affected_start_rate * 100}%`,
            width: `${(impact.comparison_start_rate - impact.affected_start_rate) * 100}%`,
          }}
        />
        <span
          className="signal-gap__marker signal-gap__marker--affected"
          style={{ left: `${impact.affected_start_rate * 100}%` }}
        />
        <span
          className="signal-gap__marker signal-gap__marker--comparison"
          style={{ left: `${impact.comparison_start_rate * 100}%` }}
        />
      </div>
      <div className="signal-gap__values">
        <div>
          <strong>{formatPercent(impact.affected_start_rate)}</strong>
          <span>Affected cohort</span>
        </div>
        <div className="signal-gap__values--right">
          <strong>{formatPercent(impact.comparison_start_rate)}</strong>
          <span>Comparison</span>
        </div>
      </div>
      <p>
        The affected cohort is taking {impact.affected_median_days - impact.comparison_median_days}{' '}
        more days to reach a treatment outcome.
      </p>
    </section>
  )
}

function ImpactLedger({ impact }: { impact: Impact }) {
  const items = [
    {
      label: 'Patients in affected cohort',
      value: impact.affected_patient_count.toLocaleString(),
      note: 'Therapy A · Northeast · Commercial',
    },
    {
      label: 'Median days to outcome',
      value: `${impact.affected_median_days} days`,
      note: `${impact.comparison_median_days} days in comparison`,
    },
    {
      label: 'Excess starts at risk',
      value: impact.estimated_excess_starts_at_risk.toLocaleString(),
      note: 'Estimated against comparison rate',
    },
    {
      label: 'Annual value at risk',
      value: formatCurrency(impact.estimated_incremental_annual_value_at_risk_usd),
      note: 'Synthetic commercial assumption',
    },
  ]
  return (
    <section className="impact-ledger" aria-label="Business impact summary">
      {items.map(item => (
        <div className="impact-ledger__item" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.note}</small>
        </div>
      ))}
    </section>
  )
}

function BarrierChart({ barriers }: { barriers: Barrier[] }) {
  const data = {
    labels: barriers.map(item => titleCase(item.barrier_category)),
    datasets: [
      {
        data: barriers.map(item => item.signal_count),
        backgroundColor: barriers.map((_, index) =>
          index === 0 ? '#2f66e8' : index === 1 ? '#18a59b' : '#b9c7d8',
        ),
        borderRadius: 5,
        borderSkipped: false,
        barThickness: 17,
      },
    ],
  }
  const options: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    animation: { duration: 450 },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          afterLabel: context => {
            const item = barriers[context.dataIndex]
            return `${(item.average_confidence * 100).toFixed(1)}% average confidence`
          },
        },
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        grid: { color: '#e5ebf2' },
        ticks: { color: '#60758a', precision: 0 },
        border: { display: false },
      },
      y: {
        grid: { display: false },
        ticks: { color: '#243b53', font: { size: 12, weight: 600 } },
        border: { display: false },
      },
    },
  }
  return <Bar data={data} options={options} />
}

function TrendChart({ trend, metric }: { trend: AccessTrend[]; metric: 'rate' | 'days' }) {
  const isRate = metric === 'rate'
  const data = {
    labels: trend.map(item => formatMonth(item.prescription_month)),
    datasets: [
      {
        data: trend.map(item =>
          isRate ? item.treatment_start_rate * 100 : item.median_days_to_outcome,
        ),
        borderColor: isRate ? '#2f66e8' : '#d97706',
        backgroundColor: isRate ? 'rgba(47, 102, 232, 0.10)' : 'rgba(217, 119, 6, 0.10)',
        fill: true,
        tension: 0.28,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: isRate ? '#2f66e8' : '#d97706',
      },
    ],
  }
  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 450 },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: context =>
            isRate ? `${Number(context.raw).toFixed(1)}% start rate` : `${context.raw} days`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#60758a' },
        border: { display: false },
      },
      y: {
        suggestedMin: isRate ? 45 : 0,
        suggestedMax: isRate ? 85 : 22,
        grid: { color: '#e5ebf2' },
        ticks: {
          color: '#60758a',
          callback: value => (isRate ? `${value}%` : `${value}`),
        },
        border: { display: false },
      },
    },
  }
  return <Line data={data} options={options} />
}

function FilterBar({
  options,
  draft,
  onChange,
  onApply,
  loading,
}: {
  options: Filters
  draft: FilterSelection
  onChange: (field: keyof FilterSelection, value: string) => void
  onApply: (event: FormEvent) => void
  loading: boolean
}) {
  return (
    <form className="filter-bar" onSubmit={onApply}>
      <label>
        Therapy
        <select value={draft.therapy} onChange={event => onChange('therapy', event.target.value)}>
          {options.therapies.map(value => <option key={value}>{value}</option>)}
        </select>
      </label>
      <label>
        Region
        <select value={draft.region} onChange={event => onChange('region', event.target.value)}>
          {options.regions.map(value => <option key={value}>{value}</option>)}
        </select>
      </label>
      <label>
        Payer
        <select value={draft.payer_type} onChange={event => onChange('payer_type', event.target.value)}>
          {options.payer_types.map(value => <option key={value}>{value}</option>)}
        </select>
      </label>
      <label>
        Signals since
        <input
          type="date"
          value={draft.start_date}
          onChange={event => onChange('start_date', event.target.value)}
        />
      </label>
      <button className="button button--primary" type="submit" disabled={loading}>
        {loading ? 'Updating…' : 'Update view'}
      </button>
    </form>
  )
}

function EvidenceDetail({ evidence, onClose }: { evidence: Evidence; onClose: () => void }) {
  return (
    <aside className="evidence-detail" aria-label={`Evidence ${evidence.feedback_id}`}>
      <div className="evidence-detail__header">
        <div>
          <span className="eyebrow">Evidence record</span>
          <h3>{evidence.feedback_id}</h3>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Close evidence detail">×</button>
      </div>
      <div className="evidence-detail__badges">
        <span className={`badge badge--${evidence.urgency}`}>{titleCase(evidence.urgency)} urgency</span>
        <span className="badge badge--neutral">{titleCase(evidence.sentiment)}</span>
        {evidence.review_required && <span className="badge badge--review">Review required</span>}
      </div>
      <section>
        <span className="field-label">AI-assisted summary</span>
        <p className="evidence-detail__summary">{evidence.signal_summary}</p>
      </section>
      <section>
        <span className="field-label">Masked source evidence</span>
        <blockquote>{evidence.evidence_excerpt}</blockquote>
      </section>
      <dl className="confidence-grid">
        <div><dt>Barrier</dt><dd>{titleCase(evidence.barrier_category)}</dd></div>
        <div><dt>Confidence</dt><dd>{formatPercent(evidence.barrier_confidence)}</dd></div>
        <div><dt>Source</dt><dd>{evidence.source}</dd></div>
        <div><dt>Received</dt><dd>{formatDate(evidence.feedback_timestamp)}</dd></div>
      </dl>
      <div className="trust-note">
        <Icon name="shield" />
        <p><strong>AI-assisted</strong><br />Verify the source evidence before using this signal in client material.</p>
      </div>
    </aside>
  )
}

function EvidenceTable({
  evidence,
  onSelect,
  emptyMessage,
}: {
  evidence: Evidence[]
  onSelect: (item: Evidence) => void
  emptyMessage: string
}) {
  if (evidence.length === 0) {
    return <div className="empty-state"><Icon name="review" /><p>{emptyMessage}</p></div>
  }
  return (
    <div className="evidence-table-wrap">
      <table className="evidence-table">
        <thead>
          <tr>
            <th>Signal</th>
            <th>Barrier</th>
            <th>Urgency</th>
            <th>Confidence</th>
            <th>Source</th>
            <th><span className="sr-only">Open</span></th>
          </tr>
        </thead>
        <tbody>
          {evidence.map(item => (
            <tr key={item.feedback_id}>
              <td>
                <strong>{item.signal_summary}</strong>
                <small>{item.feedback_id} · {formatDate(item.feedback_timestamp)}</small>
              </td>
              <td>{titleCase(item.barrier_category)}</td>
              <td><span className={`urgency-dot urgency-dot--${item.urgency}`} />{titleCase(item.urgency)}</td>
              <td>{formatPercent(item.barrier_confidence)}</td>
              <td>{item.source}</td>
              <td><button className="table-action" onClick={() => onSelect(item)}>Inspect</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ArchitectureModal({ onClose }: { onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    closeRef.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  const layers = [
    { name: 'Bronze', detail: 'Restricted raw landing', copy: 'Direct identifiers and original text remain isolated for engineering workflows.', tone: 'bronze' },
    { name: 'Silver', detail: 'De-identified and curated', copy: 'Hashed patient keys, masked text, and standardized access journeys.', tone: 'silver' },
    { name: 'AI signals', detail: 'Reviewable extraction', copy: 'Barrier, sentiment, urgency, summary, confidence, and source citations.', tone: 'ai' },
    { name: 'Gold', detail: 'Analyst-safe decisions', copy: 'Access KPIs, signal trends, evidence detail, and quantified business impact.', tone: 'gold' },
  ]
  return (
    <div className="architecture-modal" role="dialog" aria-modal="true" aria-labelledby="architecture-title">
      <header className="architecture-modal__header">
        <div>
          <span className="eyebrow">How this works</span>
          <h2 id="architecture-title">From fragmented signals to analyst action</h2>
        </div>
        <div className="architecture-modal__actions">
          <img src="/databricks-wordmark.png" alt="Databricks" />
          <button ref={closeRef} className="button button--quiet" onClick={onClose}>Close</button>
        </div>
      </header>
      <div className="architecture-modal__content">
        <section className="source-cloud">
          <div>
            <span className="eyebrow">Representative sources</span>
            <h3>Signals arrive in different shapes and systems</h3>
          </div>
          <div className="source-cloud__items">
            {['S3 vendor data', 'Snowflake', 'CRM', 'Call center', 'Surveys', 'Analyst notes'].map(source => (
              <span key={source}>{source}</span>
            ))}
          </div>
          <p>POC: synthetic files in a Unity Catalog managed volume</p>
        </section>
        <div className="flow-arrow"><Icon name="arrow" /></div>
        <section className="medallion-flow">
          {layers.map((layer, index) => (
            <div className={`architecture-layer architecture-layer--${layer.tone}`} key={layer.name}>
              <span className="architecture-layer__step">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <h3>{layer.name}</h3>
                <strong>{layer.detail}</strong>
                <p>{layer.copy}</p>
              </div>
            </div>
          ))}
        </section>
        <div className="flow-arrow"><Icon name="arrow" /></div>
        <section className="app-destination">
          <div className="app-destination__mark"><Icon name="spark" /></div>
          <div>
            <span className="eyebrow">Databricks App</span>
            <h3>Patient Signal Workbench</h3>
            <p>Secure, self-service access to the same governed Gold data—without exporting another copy.</p>
          </div>
        </section>
        <section className="production-roadmap">
          <h3>What changes for production</h3>
          <div className="production-roadmap__grid">
            <div><span>POC</span><p>Synthetic sources, deterministic masking, 1,000 AI-processed feedback records, read-only review.</p></div>
            <div><span>Production</span><p>Approved source connectors, privacy-tested policies, full-volume monitoring, persistent annotations, client isolation.</p></div>
          </div>
        </section>
      </div>
    </div>
  )
}

function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [activeFilters, setActiveFilters] = useState<FilterSelection>(initialFilters)
  const [draftFilters, setDraftFilters] = useState<FilterSelection>(initialFilters)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null)
  const [showArchitecture, setShowArchitecture] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({
      therapy: activeFilters.therapy,
      region: activeFilters.region,
      payer_type: activeFilters.payer_type,
      start_date: activeFilters.start_date,
    })
    setLoading(true)
    setError(null)
    fetch(`/api/dashboard?${params.toString()}`, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) {
          const body = await response.json().catch(() => ({ detail: 'The dashboard could not be loaded.' }))
          throw new Error(body.detail || 'The dashboard could not be loaded.')
        }
        return response.json() as Promise<DashboardResponse>
      })
      .then(data => {
        setDashboard(data)
        setSelectedEvidence(current =>
          current ? data.evidence.find(item => item.feedback_id === current.feedback_id) || null : null,
        )
      })
      .catch(fetchError => {
        if (fetchError.name !== 'AbortError') setError(fetchError.message)
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [activeFilters, reloadKey])

  const reviewEvidence = useMemo(
    () => dashboard?.evidence.filter(item => item.review_required) || [],
    [dashboard],
  )

  const applyFilters = (event: FormEvent) => {
    event.preventDefault()
    setActiveFilters(draftFilters)
  }

  const changeFilter = (field: keyof FilterSelection, value: string) => {
    setDraftFilters(current => ({ ...current, [field]: value }))
  }

  if (!dashboard && loading) {
    return (
      <main className="loading-screen" aria-live="polite">
        <div className="loading-mark"><Icon name="layers" /></div>
        <p>Assembling governed patient signals…</p>
      </main>
    )
  }

  if (!dashboard || error) {
    return (
      <main className="error-screen">
        <span className="eyebrow">Data connection</span>
        <h1>The workbench could not load its Gold data.</h1>
        <p>{error || 'No dashboard response was returned.'}</p>
        <button className="button button--primary" onClick={() => setReloadKey(value => value + 1)}>Try again</button>
      </main>
    )
  }

  const topBarrier = dashboard.barriers[0]
  const options = dashboard.filters

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="product-lockup" href="#main-content" aria-label="Patient Signal Workbench home">
          <span className="product-lockup__mark"><Icon name="spark" /></span>
          <span><strong>Patient Signal</strong><small>Workbench</small></span>
        </a>
        <nav className="primary-nav" aria-label="Primary navigation">
          {(['overview', 'explore', 'review'] as Tab[]).map(item => (
            <button
              className={tab === item ? 'primary-nav__item primary-nav__item--active' : 'primary-nav__item'}
              key={item}
              onClick={() => setTab(item)}
            >
              {item === 'review' ? `Review queue · ${dashboard.review_required_count}` : titleCase(item)}
            </button>
          ))}
        </nav>
        <div className="topbar__right">
          <button className="button button--quiet" onClick={() => setShowArchitecture(true)}>
            <Icon name="layers" /> How this works
          </button>
          <img src="/databricks-wordmark.png" alt="Databricks" className="databricks-wordmark" />
        </div>
      </header>

      <div className="disclosure-bar">
        <span>{dashboard.meta.disclosure}</span>
        <span className={dashboard.meta.is_snapshot ? 'backend-status backend-status--snapshot' : 'backend-status'}>
          {dashboard.meta.is_snapshot ? 'Gold JSON snapshot' : 'Live Gold tables'}
        </span>
      </div>

      <main id="main-content" className="main-content">
        {tab === 'overview' && (
          <>
            <section className="hero-grid">
              <div className="hero-copy">
                <span className="eyebrow">Access deterioration detected</span>
                <h1>The access signal moved.<br /><em>Here’s why.</em></h1>
                <p>
                  Therapy A starts for Northeast commercial patients fell below the comparison cohort.
                  Unstructured feedback points to authorization and pharmacy handoffs.
                </p>
                <div className="hero-actions">
                  <button className="button button--primary" onClick={() => setTab('explore')}>
                    Explore supporting signals <Icon name="arrow" />
                  </button>
                  <span>{dashboard.impact.business_signal}</span>
                </div>
              </div>
              <SignalGap impact={dashboard.impact} />
            </section>

            <ImpactLedger impact={dashboard.impact} />

            <section className="recommendation-band">
              <div className="recommendation-band__icon"><Icon name="spark" /></div>
              <div>
                <span className="eyebrow">Recommended next investigation</span>
                <h2>{dashboard.impact.recommended_action}</h2>
              </div>
              <button className="button button--quiet" onClick={() => setTab('explore')}>View evidence</button>
            </section>

            <section className="dashboard-grid">
              <article className="panel panel--barriers">
                <div className="panel__header">
                  <div>
                    <span className="eyebrow">Why starts are delayed</span>
                    <h2>Access barriers in patient feedback</h2>
                  </div>
                  {topBarrier && <span className="panel-stat">{topBarrier.signal_count} prior-auth signals</span>}
                </div>
                <div className="chart chart--bar"><BarrierChart barriers={dashboard.barriers} /></div>
              </article>
              <article className="panel panel--trend">
                <div className="panel__header">
                  <div>
                    <span className="eyebrow">Journey performance</span>
                    <h2>Treatment-start rate</h2>
                  </div>
                  <span className="panel-stat panel-stat--down">↓ 19.5 pts</span>
                </div>
                <div className="chart chart--trend"><TrendChart trend={dashboard.access_trend} metric="rate" /></div>
              </article>
            </section>

            <section className="evidence-preview">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">Evidence, not just an answer</span>
                  <h2>Signals behind the recommendation</h2>
                </div>
                <button className="button button--quiet" onClick={() => setTab('explore')}>Open signal explorer</button>
              </div>
              <EvidenceTable
                evidence={dashboard.evidence.slice(0, 4)}
                onSelect={setSelectedEvidence}
                emptyMessage="No evidence matches this cohort."
              />
            </section>
          </>
        )}

        {tab === 'explore' && (
          <>
            <section className="page-heading">
              <div><span className="eyebrow">Signal explorer</span><h1>Move from the anomaly to the evidence.</h1></div>
              <p>Every AI-assisted signal is paired with masked source text and confidence.</p>
            </section>
            <FilterBar
              options={options}
              draft={draftFilters}
              onChange={changeFilter}
              onApply={applyFilters}
              loading={loading}
            />
            <div className="active-filter-line">
              Showing {activeFilters.therapy} · {activeFilters.region} · {activeFilters.payer_type} · since {activeFilters.start_date}
            </div>
            <section className="dashboard-grid dashboard-grid--explore">
              <article className="panel panel--barriers">
                <div className="panel__header"><div><span className="eyebrow">Signal mix</span><h2>Primary barriers</h2></div></div>
                <div className="chart chart--bar"><BarrierChart barriers={dashboard.barriers} /></div>
              </article>
              <article className="panel trend-pair">
                <div className="panel__header"><div><span className="eyebrow">Over time</span><h2>Access performance</h2></div></div>
                <div className="trend-pair__charts">
                  <div><span>Treatment-start rate</span><div className="chart chart--mini"><TrendChart trend={dashboard.access_trend} metric="rate" /></div></div>
                  <div><span>Median days to outcome</span><div className="chart chart--mini"><TrendChart trend={dashboard.access_trend} metric="days" /></div></div>
                </div>
              </article>
            </section>
            <section className="evidence-preview">
              <div className="section-heading">
                <div><span className="eyebrow">Masked evidence</span><h2>{dashboard.evidence.length} signals ready to inspect</h2></div>
              </div>
              <EvidenceTable evidence={dashboard.evidence} onSelect={setSelectedEvidence} emptyMessage="Adjust the filters to find evidence." />
            </section>
          </>
        )}

        {tab === 'review' && (
          <>
            <section className="page-heading page-heading--review">
              <div><span className="eyebrow">Human oversight</span><h1>Review what the model is least certain about.</h1></div>
              <div className="review-total"><strong>{dashboard.review_required_count}</strong><span>signals require review</span></div>
            </section>
            <section className="trust-explainer">
              <Icon name="shield" />
              <div><h2>Why a signal appears here</h2><p>Low confidence, previously sensitive source text, or an extraction error. Source identifiers remain masked.</p></div>
            </section>
            <section className="evidence-preview">
              <EvidenceTable evidence={reviewEvidence} onSelect={setSelectedEvidence} emptyMessage="No sampled records currently require review." />
              <p className="read-only-note">This POC is read-only. Persisted confirmation and correction are a production extension.</p>
            </section>
          </>
        )}
      </main>

      {selectedEvidence && <EvidenceDetail evidence={selectedEvidence} onClose={() => setSelectedEvidence(null)} />}
      {showArchitecture && <ArchitectureModal onClose={() => setShowArchitecture(false)} />}
    </div>
  )
}

export default App
