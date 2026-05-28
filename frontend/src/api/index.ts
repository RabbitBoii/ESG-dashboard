import axios from 'axios'
import type { EmissionRecord, RecordDetail, Batch, UploadResult } from '../types'

const api = axios.create({
    baseURL: 'https://esg-dashboard-production-13b5.up.railway.app/api/',
})

export const uploadFile = (file: File, sourceType: string): Promise<{ data: UploadResult }> => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_type', sourceType)
    return api.post('/ingestion/upload/', form)
}

export const getBatches = (): Promise<{ data: Batch[] }> =>
    api.get('/ingestion/batches/')

export const getRecords = (params?: Record<string, string>): Promise<{ data: EmissionRecord[] }> =>
    api.get('/emissions/records/', { params })

export const getRecord = (id: string): Promise<{ data: RecordDetail }> =>
    api.get(`/emissions/records/${id}/`)

export const reviewRecord = (id: string, status: string, comment = ''): Promise<{ data: EmissionRecord }> =>
    api.patch(`/emissions/records/${id}/review/`, { status, comment })

export const getFactors = () => api.get('/emissions/factors/')