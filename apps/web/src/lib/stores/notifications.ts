import { writable } from 'svelte/store';
import { api } from '$lib/api';

interface UnreadCountResponse {
	unread_count: number;
}

export const unreadCount = writable(0);

let pollingInterval: ReturnType<typeof setInterval> | null = null;

async function fetchUnreadCount(): Promise<void> {
	try {
		const data = await api.get<UnreadCountResponse>('/notifications/unread-count');
		unreadCount.set(data.unread_count);
	} catch {
		// silently ignore — user may not be logged in
	}
}

export function startNotificationPolling(): () => void {
	fetchUnreadCount();
	pollingInterval = setInterval(fetchUnreadCount, 30_000);

	return () => {
		if (pollingInterval !== null) {
			clearInterval(pollingInterval);
			pollingInterval = null;
		}
	};
}
