import { useCallback, useEffect, useRef, useState } from 'react'

import { api, uploadFile } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'
import Icon from '../components/Icon.jsx'
import { useToast } from '../components/Toast.jsx'
import { Field } from '../components/form.jsx'
import { Badge, Button, ErrorBanner } from '../components/ui.jsx'
import { DEPARTMENTS } from '../lib/constants.js'
import { formatBytes, formatDateTime } from '../lib/format.js'

const PAGE_SIZE = 20
const MAX_UPLOAD_MB = 20 // backend: settings.max_upload_mb
const POLL_MS = 3000 // refresh while documents are being indexed
const PENDING = new Set(['uploaded', 'processing'])

const STATUS = {
  uploaded: { tone: 'amber', label: 'Queued' },
  processing: { tone: 'amber', label: 'Indexing...' },
  indexed: { tone: 'green', label: 'Indexed' },
  failed: { tone: 'red', label: 'Failed' },
}

/**
 * Faculty: their department's documents + ones shared with all departments; uploads go to their department.
 * Admin: all documents (department filter); uploads are shared with all departments.
 * Indexing runs in the background worker, so the list polls while anything is queued/indexing.
 */
export default function KnowledgePage() {
  const { user } = useAuth()
  const showToast = useToast()
  const isAdmin = user.role === 'admin'
  const department = DEPARTMENTS[user.department_id]

  const [departmentId, setDepartmentId] = useState('')
  const [offset, setOffset] = useState(0)
  const [tick, setTick] = useState(0) // bump to refetch (retry, poll, after upload)
  const [page, setPage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const lastStatus = useRef(new Map()) // id -> status, to toast when indexing finishes

  useEffect(() => {
    const request = { active: true } // ignore responses after unmount or a newer request
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset })
    if (isAdmin && departmentId) params.set('department_id', departmentId)

    api(`/documents?${params}`)
      .then((data) => {
        if (!request.active) return
        announceFinished(data.items, lastStatus.current, showToast)
        setPage(data)
        setError('')
      })
      .catch((err) => request.active && setError(err.message))
      .finally(() => request.active && setLoading(false))
    return () => {
      request.active = false
    }
  }, [departmentId, offset, tick, isAdmin, showToast])

  const items = page?.items ?? []
  const total = page?.total ?? 0
  const hasPending = items.some((d) => PENDING.has(d.status))

  // Poll quietly while anything on screen is still being indexed.
  useEffect(() => {
    if (!hasPending || error) return
    const timer = setTimeout(() => setTick((t) => t + 1), POLL_MS)
    return () => clearTimeout(timer)
  }, [hasPending, error, page])

  const refetch = (changes) => {
    setLoading(true)
    changes?.()
    setTick((t) => t + 1)
  }

  const onUploaded = useCallback(
    (doc) => {
      setUploadOpen(false)
      lastStatus.current.set(doc.id, doc.status)
      showToast(`${docName({ title: doc.title, filename: doc.original_filename })} uploaded – indexing started`)
      setLoading(true)
      setOffset(0) // newest first, so it appears on page 1
      setTick((t) => t + 1)
    },
    [showToast],
  )

  const closeUpload = useCallback(() => setUploadOpen(false), [])

  const indexedCount = items.filter((d) => d.status === 'indexed').length

  return (
    <div className="page knowledge-page">
      <div className="page-intro">
        <div>
          <h2>Knowledge base</h2>
          <p>
            {isAdmin
              ? 'Upload trusted placement material for the AI assistant. Your uploads are shared with all departments.'
              : `Upload trusted placement material for the AI assistant. Your uploads are visible to ${
                  department?.code ?? 'your'
                } students.`}
          </p>
        </div>
        {page && (
          <Badge tone="green">
            {total} {total === 1 ? 'document' : 'documents'}
          </Badge>
        )}
      </div>

      <section className="card document-card">
        <div className="card-title-row">
          <div>
            <h3>Uploaded documents</h3>
            <p>
              {hasPending
                ? 'Some documents are still being indexed – this list updates automatically.'
                : page && items.length
                  ? `${indexedCount} of ${items.length} on this page available to the AI assistant`
                  : 'Materials available to the AI assistant'}
            </p>
          </div>
          <div className="toolbar-right">
            {isAdmin && (
              <select
                className="input compact"
                aria-label="Filter by department"
                value={departmentId}
                onChange={(e) =>
                  refetch(() => {
                    setDepartmentId(e.target.value)
                    setOffset(0)
                  })
                }
              >
                <option value="">All documents</option>
                {Object.entries(DEPARTMENTS).map(([id, d]) => (
                  <option key={id} value={id}>
                    {d.code} only
                  </option>
                ))}
              </select>
            )}
            <Button variant="secondary" icon="upload" onClick={() => setUploadOpen(true)}>
              Upload file
            </Button>
          </div>
        </div>

        {error && (
          <div className="table-message">
            <ErrorBanner>{error}</ErrorBanner>
            <Button variant="secondary" onClick={() => refetch(() => setError(''))}>
              Try again
            </Button>
          </div>
        )}

        {!error && !page && (
          <div className="page-loading" role="status" aria-label="Loading documents">
            <span className="button-spinner" aria-hidden="true" />
          </div>
        )}

        {!error && page && items.length === 0 && (
          <div className="empty-mini">
            <div className="empty-art">
              <Icon name="file" size={30} />
            </div>
            <h3>No documents yet</h3>
            <p>Upload placement materials to give the assistant trusted context.</p>
            <Button icon="upload" onClick={() => setUploadOpen(true)}>
              Upload your first document
            </Button>
          </div>
        )}

        {!error && items.length > 0 && (
          <div className={`table-scroll ${loading ? 'is-refreshing' : ''}`} aria-busy={loading}>
            <table>
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Status</th>
                  <th>Chunks</th>
                  <th>Visible to</th>
                  <th>Uploaded on</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {items.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div className="file-cell">
                        <span>
                          <Icon name="file" />
                        </span>
                        <div>
                          <strong>{d.title || d.filename}</strong>
                          <small>
                            {d.title ? d.filename : null}
                            {d.title && d.description ? ' · ' : null}
                            {d.description}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <Badge tone={STATUS[d.status]?.tone}>{STATUS[d.status]?.label ?? d.status}</Badge>
                      {d.status === 'failed' && d.error && (
                        <small className="reason doc-error" title={d.error}>
                          {d.error}
                        </small>
                      )}
                    </td>
                    <td>{d.status === 'indexed' ? d.chunks : <span className="muted-text">—</span>}</td>
                    <td>{d.department_code ?? <span className="muted-text">All departments</span>}</td>
                    <td>{formatDateTime(d.uploaded_at)}</td>
                    <td>{formatBytes(d.size_bytes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!error && total > PAGE_SIZE && (
          <div className="pagination">
            <span>
              Showing {offset + 1}–{offset + items.length} of {total} documents
            </span>
            <div>
              <Button
                variant="secondary"
                disabled={loading || offset === 0}
                onClick={() => refetch(() => setOffset(Math.max(0, offset - PAGE_SIZE)))}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={loading || offset + items.length >= total}
                onClick={() => refetch(() => setOffset(offset + PAGE_SIZE))}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </section>

      {uploadOpen && (
        <UploadModal
          audience={isAdmin ? 'all departments' : `${department?.code ?? 'your department'} students`}
          onClose={closeUpload}
          onUploaded={onUploaded}
        />
      )}
    </div>
  )
}

function UploadModal({ audience, onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [fileError, setFileError] = useState('')
  const [serverError, setServerError] = useState('')
  const [progress, setProgress] = useState(null) // null = not uploading
  const uploading = progress !== null

  // Escape closes, but not mid-upload.
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && !uploading && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, uploading])

  const choose = (f) => {
    if (!f) return
    setServerError('')
    if (!/\.(pdf|txt)$/i.test(f.name)) return setFileError('Choose a PDF or TXT file')
    if (f.size > MAX_UPLOAD_MB * 1024 * 1024) return setFileError(`File must be under ${MAX_UPLOAD_MB} MB`)
    if (f.size === 0) return setFileError('This file is empty')
    setFileError('')
    setFile(f)
    // Suggest a title from the filename: "TCS_NQT_2025_Pattern.pdf" -> "TCS NQT 2025 Pattern"
    if (!title.trim()) setTitle(f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim().slice(0, 200))
  }

  const submit = async (e) => {
    e.preventDefault()
    if (uploading) return
    if (!file) return setFileError('Choose a file to upload')

    const body = new FormData()
    body.append('file', file)
    if (title.trim()) body.append('title', title.trim())
    if (description.trim()) body.append('description', description.trim())

    setServerError('')
    setProgress(0)
    try {
      const doc = await uploadFile('/documents', body, { onProgress: setProgress })
      onUploaded(doc)
    } catch (err) {
      setServerError(err.message)
      setProgress(null)
    }
  }

  return (
    <div className="modal-layer">
      <div className="modal-backdrop" onClick={() => !uploading && onClose()} />
      <form
        className="modal upload-modal"
        onSubmit={submit}
        noValidate
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
      >
        <div className="modal-head">
          <div>
            <p className="overline">KNOWLEDGE BASE</p>
            <h2 id="upload-title">Upload placement material</h2>
            <p>The assistant will use it to answer questions from {audience}.</p>
          </div>
          <button type="button" className="icon-btn" disabled={uploading} onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>

        <div className="modal-body">
          <ErrorBanner>{serverError}</ErrorBanner>

          <div className="field">
            <span className="field-label">File</span>
            <label
              className={`modal-file-picker ${file ? 'has-file' : ''} ${fileError ? 'input-error' : ''}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                if (!uploading) choose(e.dataTransfer.files[0])
              }}
            >
              <input
                type="file"
                accept=".pdf,.txt,application/pdf,text/plain"
                disabled={uploading}
                onChange={(e) => choose(e.target.files?.[0])}
              />
              <span className="upload-icon">
                <Icon name={file ? 'check' : 'upload'} size={21} />
              </span>
              <span>
                <strong>{file ? file.name : 'Choose a PDF or TXT file'}</strong>
                <small>
                  {file
                    ? `${formatBytes(file.size)} · click to choose a different file`
                    : `Drag and drop here or click to browse · Max ${MAX_UPLOAD_MB} MB`}
                </small>
              </span>
            </label>
            {fileError && <span className="validation-error">{fileError}</span>}
          </div>

          <Field label="Title" htmlFor="doc-title" hint="Optional · shown in the list instead of the filename">
            <input
              id="doc-title"
              className="input"
              value={title}
              maxLength={200}
              disabled={uploading}
              placeholder="e.g. TCS NQT 2025 Preparation Guide"
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>

          <Field label="Description" htmlFor="doc-description" hint="Optional">
            <textarea
              id="doc-description"
              className="input textarea"
              rows={3}
              value={description}
              disabled={uploading}
              placeholder="Briefly describe what this material covers..."
              onChange={(e) => setDescription(e.target.value)}
            />
          </Field>

          {uploading && (
            <div className="modal-upload-progress" role="status">
              <div>
                <span>{progress < 100 ? 'Uploading document...' : 'Saving and queueing for indexing...'}</span>
                <strong>{progress}%</strong>
              </div>
              <div className="upload-progress">
                <i style={{ width: `${progress}%`, animation: 'none' }} />
              </div>
            </div>
          )}
        </div>

        <div className="modal-actions">
          <Button variant="secondary" type="button" disabled={uploading} onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={uploading} disabled={!file}>
            {uploading ? 'Uploading...' : 'Upload and index'}
          </Button>
        </div>
      </form>
    </div>
  )
}

/** Toast for documents that went from queued/indexing to indexed/failed since the last fetch. */
function announceFinished(items, seen, showToast) {
  for (const d of items) {
    const before = seen.get(d.id)
    if (before && PENDING.has(before) && !PENDING.has(d.status)) {
      if (d.status === 'indexed') showToast(`${docName(d)} indexed – ${d.chunks} chunks`)
      else showToast(`Indexing failed for ${docName(d)}`, { tone: 'error' })
    }
    seen.set(d.id, d.status)
  }
}

function docName(d) {
  return d.title || d.filename
}
