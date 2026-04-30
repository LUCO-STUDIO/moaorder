<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { unreadCount } from '$lib/stores/notifications';

	interface Notification {
		id: string;
		type: string;
		status: string;
		title: string;
		body: string | null;
		payload: Record<string, string>;
		read_at: string | null;
		created_at: string;
	}

	interface NotificationListResponse {
		items: Notification[];
		total: number;
		page: number;
		limit: number;
		unread_count: number;
	}

	let notifications: Notification[] = $state([]);
	let total = $state(0);
	let loading = $state(true);
	let markingAll = $state(false);

	const TYPE_ICONS: Record<string, string> = {
		group_opened: '🛒',
		order_confirmed: '✅',
		order_cancelled_min_qty: '❌',
		group_cancelled_min_qty: '❌',
		order_cancelled_pre_close: '❌',
		pickup_ready: '📦',
		pickup_confirmed: '🎉',
		pickup_reminder_customer: '⏰',
		cancel_request: '❓',
		cancel_approved: '✅',
		cancel_rejected: '❌',
		group_updated: '📝',
		picking_list_ready: '📋'
	};

	function typeIcon(type: string): string {
		return TYPE_ICONS[type] ?? '🔔';
	}

	function relativeTime(iso: string): string {
		const diff = Date.now() - new Date(iso).getTime();
		const secs = Math.floor(diff / 1000);
		if (secs < 60) return '방금 전';
		const mins = Math.floor(secs / 60);
		if (mins < 60) return `${mins}분 전`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}시간 전`;
		const days = Math.floor(hours / 24);
		return `${days}일 전`;
	}

	function navTarget(notif: Notification): string | null {
		const { order_id, group_id } = notif.payload;
		if (order_id) return `/orders/${order_id}`;
		if (group_id) return `/g/${group_id}`;
		return null;
	}

	async function load() {
		loading = true;
		try {
			const data = await api.get<NotificationListResponse>('/notifications?limit=50');
			notifications = data.items;
			total = data.total;
			unreadCount.set(data.unread_count);
		} finally {
			loading = false;
		}
	}

	async function markRead(notif: Notification) {
		if (notif.read_at) {
			const target = navTarget(notif);
			if (target) goto(target);
			return;
		}
		try {
			await api.post(`/notifications/${notif.id}/read`);
			notifications = notifications.map((n) =>
				n.id === notif.id ? { ...n, read_at: new Date().toISOString() } : n
			);
			unreadCount.update((c) => Math.max(0, c - 1));
		} catch {
			// ignore
		}
		const target = navTarget(notif);
		if (target) goto(target);
	}

	async function markAllRead() {
		markingAll = true;
		try {
			await api.post('/notifications/read-all');
			notifications = notifications.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() }));
			unreadCount.set(0);
		} finally {
			markingAll = false;
		}
	}

	onMount(load);
</script>

<svelte:head>
	<title>알림 - 모아오더</title>
</svelte:head>

<main class="px-4 py-6">
	<div class="mb-4 flex items-center justify-between">
		<h1 class="text-xl font-bold text-gray-900">알림</h1>
		{#if notifications.some((n) => !n.read_at)}
			<button
				onclick={markAllRead}
				disabled={markingAll}
				class="text-sm text-primary disabled:opacity-50"
			>
				전체 읽음
			</button>
		{/if}
	</div>

	{#if loading}
		<div class="space-y-3">
			{#each Array(4) as _}
				<div class="h-16 animate-pulse rounded-xl bg-gray-100"></div>
			{/each}
		</div>
	{:else if notifications.length === 0}
		<div class="rounded-xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-400">
			새로운 알림이 없습니다
		</div>
	{:else}
		<ul class="space-y-2">
			{#each notifications as notif (notif.id)}
				<li>
					<button
						onclick={() => markRead(notif)}
						class="flex w-full items-start gap-3 rounded-xl border p-4 text-left transition-colors
							{notif.read_at
							? 'border-gray-100 bg-white text-gray-500'
							: 'border-orange-100 bg-orange-50 text-gray-900'}"
					>
						<span class="mt-0.5 shrink-0 text-2xl">{typeIcon(notif.type)}</span>
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-semibold">{notif.title}</p>
							{#if notif.body}
								<p class="mt-0.5 text-xs leading-relaxed text-gray-500">{notif.body}</p>
							{/if}
							<p class="mt-1 text-xs text-gray-400">{relativeTime(notif.created_at)}</p>
						</div>
						{#if !notif.read_at}
							<span class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-orange-500"></span>
						{/if}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</main>
