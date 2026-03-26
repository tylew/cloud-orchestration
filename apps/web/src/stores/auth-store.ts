import { create } from 'zustand'
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth'
import { auth } from '@/lib/firebase'

type AuthState = {
  user: User | null
  loading: boolean
  error: string | null
  init: () => void
  signInWithEmail: (email: string, password: string) => Promise<boolean>
  signInWithGoogle: () => Promise<boolean>
  signOut: () => Promise<void>
  getToken: () => Promise<string | null>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  loading: true,
  error: null,

  init: () => {
    onAuthStateChanged(auth, (user) => {
      set({ user, loading: false })
    })
  },

  signInWithEmail: async (email, password) => {
    set({ error: null })
    try {
      await signInWithEmailAndPassword(auth, email, password)
      return true
    } catch (err) {
      set({ error: (err as Error).message })
      return false
    }
  },

  signInWithGoogle: async () => {
    set({ error: null })
    try {
      await signInWithPopup(auth, new GoogleAuthProvider())
      return true
    } catch (err) {
      set({ error: (err as Error).message })
      return false
    }
  },

  signOut: async () => {
    await firebaseSignOut(auth)
    set({ user: null })
  },

  getToken: async () => {
    const user = get().user
    if (!user) return null
    return user.getIdToken()
  },
}))
