import type { Citation, KnowledgeDocument } from '../types'
import type { DocumentChunk } from '../api/client'

const normalize = (text: string) => text.normalize('NFKC').replace(/[\s|*_`#…]+/g, '').toLowerCase()

export function findCitationDocument(documents: KnowledgeDocument[], citation: Citation): KnowledgeDocument | undefined {
  if (citation.documentId) return documents.find(doc => doc.id === citation.documentId)
  // Old conversations may lack IDs. Never guess between duplicate filenames.
  const matches = documents.filter(doc => doc.fileName === citation.documentName && doc.knowledgeBase === citation.knowledgeBase)
  return matches.length === 1 ? matches[0] : undefined
}

function matchQuote(chunks: DocumentChunk[], quote: string): DocumentChunk | undefined {
  const needle = normalize(quote)
  if (!needle) return undefined
  return chunks.find(chunk => normalize(chunk.text).includes(needle))
    ?? (needle.length >= 24 ? chunks.find(chunk => {
      const text = normalize(chunk.text)
      return text.length >= 24 && needle.includes(text)
    }) : undefined)
}

export function locateCitation(chunks: DocumentChunk[], citation?: Citation | null): { chunkId: string; match: 'id' | 'quote' | 'section' } | null {
  if (!citation) return null
  const visible = chunks.filter(chunk => chunk.chunkType !== 'parent')
  const exact = chunks.find(chunk => chunk.id === citation.chunkId)
  if (exact) {
    if (exact.chunkType !== 'parent') return { chunkId: exact.id, match: 'id' }
    const children = visible.filter(chunk => chunk.parentId === exact.id)
    const child = matchQuote(children, citation.quote) ?? children[0]
    if (child) return { chunkId: child.id, match: 'id' }
  }
  // Re-parsing creates new chunk IDs; the persisted quotation still locates the text.
  const quoted = matchQuote(visible, citation.quote)
  if (quoted) return { chunkId: quoted.id, match: 'quote' }
  const section = citation.section.trim()
  if (section && !['正文', '表格', '未知'].includes(section)) {
    const match = visible.find(chunk => chunk.section === section || chunk.headingPath === section)
    if (match) return { chunkId: match.id, match: 'section' }
  }
  return null
}

export function parseTableRows(tableJson?: string | null): string[][] | null {
  if (!tableJson) return null
  try {
    const parsed: unknown = JSON.parse(tableJson)
    if (!parsed || typeof parsed !== 'object') return null
    const table = parsed as { rows?: unknown; cells?: unknown }
    const rows = table.rows ?? table.cells
    if (!Array.isArray(rows) || !rows.length || !rows.every(Array.isArray)) return null
    return rows.map(row => row.map(cell => {
      if (cell && typeof cell === 'object') return String(cell.text ?? cell.content ?? '')
      return String(cell ?? '')
    }))
  } catch { return null }
}
