import { create } from 'zustand'
import {
  doc,
  collection,
  onSnapshot,
  query,
  orderBy,
  limit,
  type Unsubscribe,
} from 'firebase/firestore'
import { db } from '@/lib/firebase'

type InsightState = {
  tenantId: string | null
  projectRefId: string | null
  env: string
  project: Record<string, unknown> | null
  nodes: Record<string, unknown>[]
  validation: Record<string, unknown> | null
  activity: Record<string, unknown>[]
  deployStatus: Record<string, unknown>[]
  loading: boolean
  connected: boolean
  error: string | null

  subscribe: (tenantId: string, projectRefId: string, env: string) => void
  setEnv: (env: string) => void
  cleanup: () => void
}

let unsubscribers: Unsubscribe[] = []

export const useInsightStore = create<InsightState>((set, get) => ({
  tenantId: null,
  projectRefId: null,
  env: 'dev',
  project: null,
  nodes: [],
  validation: null,
  activity: [],
  deployStatus: [],
  loading: true,
  connected: false,
  error: null,

  subscribe: (tenantId, projectRefId, env) => {
    // Clean up previous subscriptions
    get().cleanup()

    set({ tenantId, projectRefId, env, loading: true, error: null })

    // 1. Project doc
    const projectRef = doc(db, 'tenants', tenantId, 'projects', projectRefId)
    unsubscribers.push(
      onSnapshot(
        projectRef,
        (snap) => {
          if (snap.exists()) {
            set({ project: snap.data() as Record<string, unknown>, connected: true })
          }
        },
        (err) => {
          set({ connected: false, error: `Connection lost: ${err.message}` })
        },
      ),
    )

    // 2. Nodes collection
    const nodesRef = collection(
      db,
      'tenants',
      tenantId,
      'projects',
      projectRefId,
      'blueprints',
      env,
      'nodes',
    )
    unsubscribers.push(
      onSnapshot(
        nodesRef,
        (snap) => {
          const nodes = snap.docs.map((d) => ({ id: d.id, ...d.data() }))
          set({ nodes, loading: false })
        },
        (err) => {
          set({ connected: false, error: `Connection lost: ${err.message}` })
        },
      ),
    )

    // 3. Validation doc
    const validationRef = doc(
      db,
      'tenants',
      tenantId,
      'projects',
      projectRefId,
      'blueprints',
      env,
      'validation',
      'current',
    )
    unsubscribers.push(
      onSnapshot(
        validationRef,
        (snap) => {
          set({ validation: snap.exists() ? (snap.data() as Record<string, unknown>) : null })
        },
        (err) => {
          set({ connected: false, error: `Connection lost: ${err.message}` })
        },
      ),
    )

    // 4. Activity collection (latest 50)
    const activityRef = query(
      collection(db, 'tenants', tenantId, 'projects', projectRefId, 'activity'),
      orderBy('timestamp', 'desc'),
      limit(50),
    )
    unsubscribers.push(
      onSnapshot(
        activityRef,
        (snap) => {
          const activity = snap.docs.map((d) => ({ id: d.id, ...d.data() }))
          set({ activity })
        },
        (err) => {
          set({ connected: false, error: `Connection lost: ${err.message}` })
        },
      ),
    )
  },

  setEnv: (env) => {
    const { tenantId, projectRefId } = get()
    if (tenantId && projectRefId) {
      get().subscribe(tenantId, projectRefId, env)
    }
  },

  cleanup: () => {
    unsubscribers.forEach((unsub) => unsub())
    unsubscribers = []
    set({
      project: null,
      nodes: [],
      validation: null,
      activity: [],
      deployStatus: [],
      loading: true,
      connected: false,
      error: null,
    })
  },
}))
