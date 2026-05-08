<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';

	interface OrderSummaryItem {
		id: string;
		group_id: string;
		store_id: string;
		status: string;
		status_label: string;
		status_sub: string;
		product_name: string;
		store_name: string;
		quantity: number;
		current_quantity: number;
		total_amount: number;
		current_amount: number;
		group_closes_at: string;
		group_status: string;
		created_at: string;
	}

	interface OrderListResponse {
		items: OrderSummaryItem[];
		total: number;
		page: number;
		limit: number;
	}

	let tab: 'active' | 'completed' = $state('active');
	let items: OrderSummaryItem[] = $state([]);
	let total = $state(0);
	let currentPage = $state(1);
	let loading = $state(true);
	let loadingMore = $state(false);

	const statusBadgeClass: Record<string, string> = {
		paid: 'bg-primary/10 text-primary',
		confirmed: 'bg-amber-50 text-amber-700',
		pickup_ready: 'bg-emerald-50 text-emerald-700',
		picked_up: 'bg-muted text-muted-foreground',
		not_picked_up: 'bg-destructive/10 text-destructive',
		cancelled: 'bg-muted text-muted-foreground'
	};

	async function fetchOrders() {
		loading = true;
		try {
			const data = await api.get<OrderListResponse>(
				`/orders/my?tab=${tab}&page=${currentPage}&limit=20`
			);
			items = data.items;
			total = data.total;
		} catch {
			items = [];
			total = 0;
		} finally {
			loading = false;
		}
	}

	async function switchTab(newTab: 'active' | 'completed') {
		if (tab === newTab) return;
		tab = newTab;
		currentPage = 1;
		await fetchOrders();
	}

	async function loadMore() {
		loadingMore = true;
		try {
			const data = await api.get<OrderListResponse>(
				`/orders/my?tab=${tab}&page=${currentPage + 1}&limit=20`
			);
			items = [...items, ...data.items];
			currentPage += 1;
		} catch {
			// noop
		} finally {
			loadingMore = false;
		}
	}

	onMount(fetchOrders);
</script>

<svelte:head>
	<title>주문내역 - 모아오더</title>
</svelte:head>

<div class="px-4 pt-6 pb-4 md:px-0 md:pt-10">
	<h1 class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[32px]">
		주문 내역
	</h1>
</div>

<!-- Tabs -->
<div class="flex border-b border-border px-4 md:px-0">
	{#each [{ key: 'active', label: '진행중' }, { key: 'completed', label: '완료' }] as t}
		<button
			class="flex-1 py-3.5 text-[14px] font-semibold transition-colors {tab === t.key
				? 'border-b-2 border-foreground text-foreground'
				: 'text-muted-foreground hover:text-foreground'}"
			onclick={() => switchTab(t.key as 'active' | 'completed')}
		>
			{t.label}
		</button>
	{/each}
</div>

<div class="space-y-3 px-4 py-5 md:px-0">
	{#if loading}
		<!-- Skeleton -->
		{#each [0, 1, 2] as _}
			<div class="rounded-xl bg-muted animate-pulse h-20"></div>
		{/each}
	{:else if items.length === 0}
		<!-- Empty state -->
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">📋</div>
			<div class="space-y-1.5">
				<p class="text-[15px] font-bold text-foreground">
					{tab === 'active' ? '진행 중인 주문이 없어요' : '완료된 주문이 없어요'}
				</p>
				<p class="text-[13px] text-muted-foreground">
					{tab === 'active' ? '공구 링크로 첫 주문을 해보세요' : '완료된 주문이 여기 표시돼요'}
				</p>
			</div>
		</div>
	{:else}
		<ul class="space-y-2.5">
			{#each items as item}
				<li>
					<a
						href="/orders/{item.id}"
						class="flex items-start justify-between gap-3 rounded-xl bg-card ring-1 ring-border px-4 py-4 hover:ring-primary/30 transition-all active:scale-[0.99]"
					>
						<div class="min-w-0 space-y-1">
							<p class="text-xs text-muted-foreground">{item.store_name}</p>
							<p class="text-sm font-semibold text-foreground truncate">{item.product_name}</p>
							<div class="flex items-center gap-2 text-xs text-muted-foreground">
								<span>{item.current_quantity}개</span>
								<span>·</span>
								<span class="font-medium text-foreground">₩{item.current_amount.toLocaleString()}</span>
								<span>·</span>
								<span>{new Date(item.created_at).toLocaleDateString('ko-KR')}</span>
							</div>
							{#if item.status_sub}
								<p class="text-xs text-muted-foreground/70">{item.status_sub}</p>
							{/if}
						</div>
						<span class="shrink-0 rounded-full px-2.5 py-1 text-xs font-medium {statusBadgeClass[item.status] ?? 'bg-muted text-muted-foreground'}">
							{item.status_label}
						</span>
					</a>
				</li>
			{/each}
		</ul>

		{#if total > items.length}
			<button
				class="flex w-full items-center justify-center gap-2 py-3 text-sm font-medium text-muted-foreground border border-border rounded-xl hover:bg-muted transition-colors disabled:opacity-50"
				onclick={loadMore}
				disabled={loadingMore}
			>
				{#if loadingMore}
					<span class="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"></span>
				{/if}
				더 보기 ({items.length}/{total})
			</button>
		{/if}
	{/if}
</div>
