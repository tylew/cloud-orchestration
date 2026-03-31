import { useAuthStore } from '@/stores/auth-store';
async function request(method, url, body) {
    try {
        const token = await useAuthStore.getState().getToken();
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        if (body) {
            headers['Content-Type'] = 'application/json';
        }
        const res = await fetch(url, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            return { ok: false, status: res.status, error: data };
        }
        return { ok: true, status: res.status, data: data };
    }
    catch (err) {
        return { ok: false, status: 0, error: err };
    }
}
export const api = {
    get: (url) => request('GET', url),
    post: (url, body) => request('POST', url, body),
    put: (url, body) => request('PUT', url, body),
    patch: (url, body) => request('PATCH', url, body),
    delete: (url) => request('DELETE', url),
};
