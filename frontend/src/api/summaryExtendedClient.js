import axios from 'axios'

const extendedApi = axios.create({
  baseURL: '/api/summary',
  timeout: 300000,
})

export async function generateMindMap(taskId) {
  const { data } = await extendedApi.post('/mindmap', { task_id: taskId })
  return data
}

export async function sendSummaryChat(taskId, message, history = []) {
  const { data } = await extendedApi.post('/chat', {
    task_id: taskId,
    message,
    history,
  })
  return data
}
