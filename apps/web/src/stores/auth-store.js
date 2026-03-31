import { create } from 'zustand';
import { onAuthStateChanged, signInWithEmailAndPassword, signInWithPopup, GoogleAuthProvider, signOut as firebaseSignOut, } from 'firebase/auth';
import { auth } from '@/lib/firebase';
export const useAuthStore = create((set, get) => ({
    user: null,
    loading: true,
    error: null,
    init: () => {
        onAuthStateChanged(auth, (user) => {
            set({ user, loading: false });
        });
    },
    signInWithEmail: async (email, password) => {
        set({ error: null });
        try {
            await signInWithEmailAndPassword(auth, email, password);
            return true;
        }
        catch (err) {
            set({ error: err.message });
            return false;
        }
    },
    signInWithGoogle: async () => {
        set({ error: null });
        try {
            await signInWithPopup(auth, new GoogleAuthProvider());
            return true;
        }
        catch (err) {
            set({ error: err.message });
            return false;
        }
    },
    signOut: async () => {
        await firebaseSignOut(auth);
        set({ user: null });
    },
    getToken: async () => {
        const user = get().user;
        if (!user)
            return null;
        return user.getIdToken();
    },
}));
