<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';

	interface TodayPickupItem {
		order_id: string;
		group_id: string;
		product_name: string;
		store_name: string;
		quantity: number;
		group_status: string;
		pickup_label: string;
	}

	interface ActiveOrderItem {
		order_id: string;
		group_id: string;
		product_name: string;
		store_name: string;
		quantity: number;
		total_amount: number;
		status: string;
		status_label: string;
		status_sub: string;
	}

	interface FeedItem {
		public_id: string;
		group_id: string;
		store_id: string;
		store_name: string;
		product_name: string;
		price: number;
		image_url: string | null;
		closes_at: string;
		remaining_qty: number | null;
	}

	let todayPickups: TodayPickupItem[] = $state([]);
	let activeOrders: ActiveOrderItem[] = $state([]);
	let feed: FeedItem[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	function timeUntil(closesAt: string): string {
		const diff = new Date(closesAt).getTime() - Date.now();
		if (diff <= 0) return '마감됨';
		const hours = Math.floor(diff / 3_600_000);
		const mins = Math.floor((diff % 3_600_000) / 60_000);
		if (hours > 0) return `${hours}시간 ${mins}분 후 마감`;
		return `${mins}분 후 마감`;
	}

	const statusBadgeClass: Record<string, string> = {
		paid: 'bg-blue-100 text-blue-700',
		confirmed: 'bg-amber-100 text-amber-700',
		pickup_ready: 'bg-green-100 text-green-700'
	};

	onMount(async () => {
		try {
			[todayPickups, activeOrders, feed] = await Promise.all([
				api.get<TodayPickupItem[]>('/home/today-pickup'),
				api.get<ActiveOrderItem[]>('/home/my-orders-active'),
				api.get<FeedItem[]>('/home/feed')
			]);
		} catch {
			error = '홈 피드를 불러오지 못했습니다';
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>홈 - 모아오더</title>
</svelte:head>

<div class="px-4 pt-5 pb-2 flex items-center justify-between">
	<h1 class="text-xl font-bold text-foreground">홈</h1>
</div>

<div class="px-4 pb-6 space-y-6">
	{#if loading}
		<!-- Skeleton loading -->
		<div class="space-y-3">
			<div class="h-4 w-24 bg-muted animate-pulse rounded-md"></div>
			{#each [0, 1] as _}
				<div class="rounded-xl bg-muted animate-pulse h-16"></div>
			{/each}
		</div>
		<div class="space-y-3">
			<div class="h-4 w-28 bg-muted animate-pulse rounded-md"></div>
			{#each [0, 1, 2] as _}
				<div class="rounded-xl bg-muted animate-pulse h-32"></div>
			{/each}
		</div>
	{:else if error}
		<!-- Error state -->
		<div class="flex flex-col items-center gap-3 py-16 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-sm font-medium text-foreground">{error}</p>
			<button
				class="text-sm text-primary underline underline-offset-2"
				onclick={() => { error = ''; loading = true; window.location.reload(); }}
			>
				다시 시도
			</button>
		</div>
	{:else}
		<!-- 오늘 수령 예정 -->
		{#if todayPickups.length > 0}
			<section class="space-y-2.5">
				<h2 class="text-sm font-semibold text-foreground">오늘 수령 예정</h2>
				<ul class="space-y-2">
					{#each todayPickups as item}
						<li>
							<a
								href="/orders/{item.order_id}"
								class="flex items-center justify-between rounded-xl bg-card ring-1 ring-border px-4 py-3.5 hover:ring-primary/30 transition-all active:scale-[0.99]"
							>
								<div class="min-w-0">
									<p class="text-sm font-semibold text-foreground truncate">{item.product_name}</p>
									<p class="text-xs text-muted-foreground mt-0.5">{item.store_name} · {item.quantity}개</p>
								</div>
								<span class="ml-3 shrink-0 rounded-full px-2.5 py-1 text-xs font-medium {item.group_status === 'pickup_ready' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}">
									{item.pickup_label}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- 진행 중 주문 -->
		{#if activeOrders.length > 0}
			<section class="space-y-2.5">
				<h2 class="text-sm font-semibold text-foreground">진행 중 주문</h2>
				<ul class="space-y-2">
					{#each activeOrders as order}
						<li>
							<a
								href="/orders/{order.order_id}"
								class="flex items-center justify-between rounded-xl bg-card ring-1 ring-border px-4 py-3.5 hover:ring-primary/30 transition-all active:scale-[0.99]"
							>
								<div class="min-w-0">
									<p class="text-sm font-semibold text-foreground truncate">{order.product_name}</p>
									<p class="text-xs text-muted-foreground mt-0.5">
										{order.store_name} · {order.quantity}개 · ₩{order.total_amount.toLocaleString()}
									</p>
									{#if order.status_sub}
										<p class="text-xs text-muted-foreground/70 mt-0.5">{order.status_sub}</p>
									{/if}
								</div>
								<span class="ml-3 shrink-0 rounded-full px-2.5 py-1 text-xs font-medium {statusBadgeClass[order.status] ?? 'bg-muted text-muted-foreground'}">
									{order.status_label}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- 구독 매장 공구 피드 -->
		<section class="space-y-2.5">
			<h2 class="text-sm font-semibold text-foreground">구독 매장 공구</h2>

			{#if feed.length === 0}
				<!-- Empty state -->
				<div class="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-card py-12 text-center">
					<div class="text-3xl">🛍️</div>
					<div class="space-y-1">
						<p class="text-sm font-medium text-foreground">진행 중인 공구가 없어요</p>
						<p class="text-xs text-muted-foreground">공구 링크를 통해 주문하면 자동으로 구독돼요</p>
					</div>
				</div>
			{:else}
				<ul class="space-y-3">
					{#each feed as item}
						<li>
							<a
								href="/g/{item.public_id}"
								class="block rounded-xl bg-card ring-1 ring-border overflow-hidden hover:ring-primary/30 transition-all active:scale-[0.99]"
							>
								{#if item.image_url}
									<img
										src={item.image_url}
										alt={item.product_name}
										class="w-full h-40 object-cover"
									/>
								{:else}
									<div class="w-full h-32 bg-muted flex items-center justify-center text-3xl">📦</div>
								{/if}
								<div class="px-4 py-3.5 space-y-1">
									<p class="text-xs text-muted-foreground">{item.store_name}</p>
									<p class="text-sm font-semibold text-foreground">{item.product_name}</p>
									<div class="flex items-center justify-between pt-0.5">
										<p class="text-base font-bold text-primary">
											₩{item.price.toLocaleString()}
										</p>
										<div class="flex items-center gap-2 text-xs text-muted-foreground">
											{#if item.remaining_qty !== null}
												<span>잔여 {item.remaining_qty}개</span>
											{/if}
											<span class="text-primary/80 font-medium">{timeUntil(item.closes_at)}</span>
										</div>
									</div>
								</div>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}
</div>
