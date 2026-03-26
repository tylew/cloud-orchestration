export type ApiResult<T> = {
  ok: boolean
  status: number
  data?: T
  error?: unknown
}
