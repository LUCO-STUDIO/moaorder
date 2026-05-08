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

<main class="px-4 pt-6 pb-8 md:px-0 md:pt-10">
	<div class="mb-5 flex items-end justify-between">
		<h1 class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[32px]">
			알림
		</h1>
		{#if notifications.some((n) => !n.read_at)}
			<button
				onclick={markAllRead}
				disabled={markingAll}
				class="text-[13px] font-semibold text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
			>
				전체 읽음
			</button>
		{/if}
	</div>

	{#if loading}
		<div class="space-y-3">
			{#each Array(4) as _}
				<div class="h-20 animate-pulse rounded-xl bg-muted"></div>
			{/each}
		</div>
	{:else if notifications.length === 0}
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">🔔</div>
			<div class="space-y-1.5">
				<p class="text-[15px] font-bold text-foreground">새로운 알림이 없어요</p>
				<p class="text-[13px] text-muted-foreground">중요한 소식이 도착하면 여기에 보여드릴게요</p>
			</div>
		</div>
	{:else}
		<ul class="space-y-2.5">
			{#each notifications as notif (notif.id)}
				<li>
					<button
						onclick={() => markRead(notif)}
						class="flex w-full items-start gap-3 rounded-2xl px-5 py-4 text-left transition-colors {notif.read_at
							? 'bg-card ring-1 ring-border'
							: 'bg-primary/5 ring-1 ring-primary/20'}"
					>
						<span class="mt-0.5 shrink-0 text-2xl">{typeIcon(notif.type)}</span>
						<div class="min-w-0 flex-1">
							<p class="truncate text-[14px] font-semibold {notif.read_at ? 'text-muted-foreground' : 'text-foreground'}">
								{notif.title}
							</p>
							{#if notif.body}
								<p class="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{notif.body}</p>
							{/if}
							<p class="mt-1.5 text-[12px] text-muted-foreground/70">{relativeTime(notif.created_at)}</p>
						</div>
						{#if !notif.read_at}
							<span class="mt-1.5 size-2 shrink-0 rounded-full bg-primary"></span>
						{/if}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</main>
