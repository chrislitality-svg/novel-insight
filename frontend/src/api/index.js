import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 30000 })

export const api = {
  uploadBook(file, onProgress) {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/books/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
      onUploadProgress: onProgress,
    })
  },
  importFolder: (folder_path, title) => http.post('/books/import-folder', { folder_path, title }, { timeout: 120000 }),
  listBooks: () => http.get('/books'),
  getBook: (id) => http.get(`/books/${id}`),
  deleteBook: (id) => http.delete(`/books/${id}`),

  startAnalyze: (id) => http.post(`/books/${id}/analyze`),
  resumeAnalyze: (id) => http.post(`/books/${id}/resume`),
  stopAnalyze: (id) => http.post(`/books/${id}/stop`),
  getProgress: (id) => http.get(`/books/${id}/progress`),

  listChapters: (id) => http.get(`/books/${id}/chapters`),
  getChapter: (cid) => http.get(`/chapters/${cid}`),
  getBehavior: (cid, config) => http.get(`/chapters/${cid}/behavior`, config),
  getDialogues: (cid, config) => http.get(`/chapters/${cid}/dialogues`, config),

  listCharacters: (id) => http.get(`/books/${id}/characters`),
  getCharacter: (cid) => http.get(`/characters/${cid}`),
  listClusters: (id) => http.get(`/books/${id}/clusters`),
  getCluster: (cid) => http.get(`/clusters/${cid}`),
  listRules: (id) => http.get(`/books/${id}/rules`),
  familyInsights: (id) => http.get(`/books/${id}/family`),
  tallyTimeline: (id) => http.get(`/books/${id}/tally-timeline`),

  behaviorCards: (id, params) => http.get(`/books/${id}/cards/behavior`, { params }),
  dialogueCards: (id, params) => http.get(`/books/${id}/cards/dialogue`, { params }),
  search: (q, bookId) => http.get('/search', { params: { q, book_id: bookId } }),
  compare: (a, b) => http.get('/compare', { params: { a, b } }),
  stats: (id) => http.get(`/books/${id}/stats`),

  exportMarkdownUrl: (id) => `/api/books/${id}/export/markdown`,
  exportTagUrl: (id, tag) => `/api/books/${id}/export/tag/${encodeURIComponent(tag)}`,
  exportCharacterUrl: (id, cid) => `/api/books/${id}/export/character/${cid}`,
}

// WebSocket 进度;返回的对象带 close()
export function connectProgress(bookId, onMessage) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws/progress/${bookId}`)
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) } catch { /* ignore */ }
  }
  return ws
}
