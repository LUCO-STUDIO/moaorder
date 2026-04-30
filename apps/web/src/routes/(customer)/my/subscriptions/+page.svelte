<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';

	interface Subscription {
		id: string;
		store_id: string;
		store_name: string;
		store_category: string | null;
		created_at: string;
	}

	let subscriptions = $state<Subscription[]>([]);
	let loading = $state(true);

	onMount(loadSubscriptions);

	async function loadSubscriptions() {
		loading = true;
		try {
			subscriptions = await api.get<Subscription[]>('/subscriptions/my');
		} catch {
			subscriptions = [];
		} finally {
			loading = false;
		}
	}

	async function handleUnsubscribe(storeId: string, storeName: string) {
		try {
			await api.delete(`/subscriptions/stores/${storeId}`);
			subscriptions = subscriptions.filter((s) => s.store_id !== storeId);
			toast.success(`${storeName} 구독이 해제되었습니다`);
		} catch {
			toast.error('구독 해제에 실패했습니다');
		}
	}
</script>

<svelte:head>
	<title>매장 구독 관리 - 모아오더</title>
</svelte:head>

<!-- Header -->
<div class="sticky top-0 z-10 flex items-center h-14 px-4 border-b border-border bg-background/95 backdrop-blur-sm">
	<a href="/my" class="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted transition-colors -ml-2" aria-label="뒤로 가기">
		<svg class="size-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
		</svg>
	</a>
	<h1 class="ml-2 text-base font-semibold text-foreground">매장 구독 관리</h1>
</div>

<div class="px-4 py-4 space-y-3">
	{#if loading}
		{#each [0, 1, 2] as _}
			<div class="h-16 rounded-xl bg-muted animate-pulse"></div>
		{/each}
	{:else if subscriptions.length === 0}
		<div class="flex flex-col items-center gap-3 py-16 text-center">
			<div class="text-3xl">🏪</div>
			<div class="space-y-1">
				<p class="text-sm font-semibold text-foreground">구독 중인 매장이 없어요</p>
				<p class="text-xs text-muted-foreground">공구에 참여하면 자동으로 매장이 구독됩니다</p>
			</div>
		</div>
	{:else}
		{#each subscriptions as sub}
			<div class="flex items-center justify-between rounded-xl bg-card ring-1 ring-border px-4 py-3.5">
				<div class="space-y-0.5">
					<p class="text-sm font-semibold text-foreground">{sub.store_name}</p>
					{#if sub.store_category}
						<p class="text-xs text-muted-foreground">{sub.store_category}</p>
					{/if}
				</div>
				<Button variant="outline" size="sm" onclick={() => handleUnsubscribe(sub.store_id, sub.store_name)}>
					구독 해제
				</Button>
			</div>
		{/each}
	{/if}
</div>
