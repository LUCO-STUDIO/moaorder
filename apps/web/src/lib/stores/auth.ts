import { writable, derived } from 'svelte/store';
import { api } from '$lib/api';

export interface AuthUser {
	id: string;
	kakao_id: string | null;
	role: 'owner' | 'customer';
	nickname: string | null;
	phone: string | null;
	region: string | null;
	category: string | null;
	email: string | null;
	email_verified: boolean;
}

const userStore = writable<AuthUser | null>(null);
const loadingStore = writable(true);

export const user = { subscribe: userStore.subscribe };
export const authLoading = { subscribe: loadingStore.subscribe };
export const isLoggedIn = derived(userStore, ($user) => $user !== null);
export const role = derived(userStore, ($user) => $user?.role ?? null);

export async function fetchMe(): Promise<AuthUser | null> {
	try {
		loadingStore.set(true);
		const data = await api.get<AuthUser>('/auth/me');
		userStore.set(data);
		return data;
	} catch {
		userStore.set(null);
		return null;
	} finally {
		loadingStore.set(false);
	}
}

export async function logout(): Promise<void> {
	await api.post('/auth/logout');
	userStore.set(null);
}

export function setUser(u: AuthUser): void {
	userStore.set(u);
	loadingStore.set(false);
}

export function clearUser(): void {
	userStore.set(null);
	loadingStore.set(false);
}
