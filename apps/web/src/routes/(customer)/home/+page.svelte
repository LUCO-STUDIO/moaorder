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

	import { user, fetchMe } from '$lib/stores/auth';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { IconPlus } from '@tabler/icons-svelte';

	import { REGIONS } from '$lib/regions';
	import { CATEGORIES } from '$lib/categories';

	let todayPickups: TodayPickupItem[] = $state([]);
	let activeOrders: ActiveOrderItem[] = $state([]);
	let feed: FeedItem[] = $state([]);
	let subscribedFeed: FeedItem[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let regionPickerOpen = $state(false);
	let savingRegion = $state(false);
	let regionSearch = $state('');
	let activeCategory = $state<string | null>(null);

	const currentRegion = $derived($user?.region ?? '');
	const filteredRegions = $derived(
		regionSearch.trim()
			? REGIONS.filter((r) => r.includes(regionSearch.trim()))
			: REGIONS
	);

	function isClosingSoon(closesAt: string): boolean {
		const diff = new Date(closesAt).getTime() - Date.now();
		return diff > 0 && diff <= 24 * 3_600_000;
	}

	function timeUntil(closesAt: string): string {
		const diff = new Date(closesAt).getTime() - Date.now();
		if (diff <= 0) return '마감됨';
		const hours = Math.floor(diff / 3_600_000);
		const mins = Math.floor((diff % 3_600_000) / 60_000);
		if (hours > 0) return `${hours}시간 ${mins}분 후 마감`;
		return `${mins}분 후 마감`;
	}

	const statusBadgeClass: Record<string, string> = {
		paid: 'bg-primary/10 text-primary',
		confirmed: 'bg-amber-50 text-amber-700',
		pickup_ready: 'bg-emerald-50 text-emerald-700'
	};

	async function loadFeed() {
		try {
			const params = new URLSearchParams();
			if (activeCategory) params.set('category', activeCategory);
			const feedQuery = params.toString() ? `/home/feed?${params}` : '/home/feed';
			[todayPickups, activeOrders, feed, subscribedFeed] = await Promise.all([
				api.get<TodayPickupItem[]>('/home/today-pickup'),
				api.get<ActiveOrderItem[]>('/home/my-orders-active'),
				api.get<FeedItem[]>(feedQuery),
				api.get<FeedItem[]>('/home/feed/subscribed')
			]);
		} catch {
			error = '홈 피드를 불러오지 못했습니다';
		} finally {
			loading = false;
		}
	}

	function handleCreateGroup() {
		if ($user?.is_owner) {
			goto('/owner/groups/create');
		} else {
			goto('/onboarding/owner');
		}
	}

	async function selectCategory(value: string | null) {
		if (activeCategory === value) {
			activeCategory = null;
		} else {
			activeCategory = value;
		}
		loading = true;
		await loadFeed();
	}

	async function selectRegion(region: string) {
		savingRegion = true;
		try {
			await api.patch('/users/me', { region });
			await fetchMe();
			regionPickerOpen = false;
			toast.success(`${region}으로 설정했어요`);
			loading = true;
			await loadFeed();
		} catch {
			toast.error('지역 설정에 실패했어요');
		} finally {
			savingRegion = false;
		}
	}

	onMount(loadFeed);
</script>

<svelte:head>
	<title>홈 - 모아오더</title>
</svelte:head>

<div class="flex items-center justify-between px-4 pt-6 pb-3 md:px-0 md:pt-8">
	<h1 class="text-[24px] font-black tracking-[-0.03em] text-foreground sm:text-[28px]">홈</h1>
	<button
		type="button"
		onclick={() => (regionPickerOpen = true)}
		class="flex items-center gap-1.5 rounded-full bg-card px-3.5 py-2 text-[13px] font-semibold text-foreground ring-1 ring-border transition-all hover:bg-muted active:scale-[0.97]"
	>
		<span aria-hidden="true">📍</span>
		<span>{currentRegion || '동네 설정'}</span>
	</button>
</div>

<div class="space-y-10 px-4 pb-8 md:px-0 md:space-y-12">
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
			<section class="space-y-3 sm:space-y-4">
				<h2 class="text-[17px] font-bold tracking-[-0.02em] text-foreground sm:text-[20px]">오늘 수령 예정</h2>
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
			<section class="space-y-3 sm:space-y-4">
				<h2 class="text-[17px] font-bold tracking-[-0.02em] text-foreground sm:text-[20px]">진행 중 주문</h2>
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

		<!-- 내 구독 매장 공구 -->
		{#if subscribedFeed.length > 0}
			<section class="space-y-3 sm:space-y-4">
				<h2 class="text-[17px] font-bold tracking-[-0.02em] text-foreground sm:text-[20px]">내 구독 매장 공구</h2>
				<ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each subscribedFeed as item}
						<li>
							<a
								href="/g/{item.public_id}"
								class="block overflow-hidden rounded-xl bg-card ring-1 ring-border transition-all hover:ring-primary/30 active:scale-[0.99]"
							>
								{#if item.image_url}
									<img src={item.image_url} alt={item.product_name} class="h-40 w-full object-cover" />
								{:else}
									<div class="flex h-32 w-full items-center justify-center bg-muted text-3xl">📦</div>
								{/if}
								<div class="space-y-1 px-4 py-3.5">
									<p class="text-xs text-muted-foreground">{item.store_name}</p>
									<p class="text-sm font-semibold text-foreground">{item.product_name}</p>
									<div class="flex items-center justify-between pt-0.5">
										<p class="text-base font-bold text-primary">₩{item.price.toLocaleString()}</p>
										<div class="flex items-center gap-2 text-xs text-muted-foreground">
											{#if item.remaining_qty !== null}
												<span>잔여 {item.remaining_qty}개</span>
											{/if}
											<span class="font-medium {isClosingSoon(item.closes_at) ? 'text-destructive' : 'text-primary/80'}">{timeUntil(item.closes_at)}</span>
										</div>
									</div>
								</div>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- 카테고리 칩 -->
		<section class="space-y-3 sm:space-y-4">
			<div class="-mx-4 overflow-x-auto px-4 md:mx-0 md:overflow-visible md:px-0">
				<ul class="flex gap-2 whitespace-nowrap md:flex-wrap">
					<li>
						<button
							type="button"
							onclick={() => selectCategory(null)}
							class="flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors {activeCategory === null ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:bg-muted'}"
						>
							전체
						</button>
					</li>
					{#each CATEGORIES as cat}
						{@const active = activeCategory === cat.value}
						<li>
							<button
								type="button"
								onclick={() => selectCategory(cat.value)}
								class="flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors {active ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:bg-muted'}"
							>
								<span aria-hidden="true">{cat.emoji}</span>
								{cat.label}
							</button>
						</li>
					{/each}
				</ul>
			</div>
		</section>

		<!-- 동네 공동구매 피드 -->
		<section class="space-y-3 sm:space-y-4">
			<div class="flex items-end justify-between">
				<h2 class="text-[17px] font-bold tracking-[-0.02em] text-foreground sm:text-[20px]">
					{#if currentRegion}
						{currentRegion} 공동구매
					{:else}
						진행 중인 공동구매
					{/if}
					{#if activeCategory}
						{@const cat = CATEGORIES.find((c) => c.value === activeCategory)}
						{#if cat}
							<span class="text-muted-foreground"> · {cat.label}</span>
						{/if}
					{/if}
				</h2>
				{#if !currentRegion}
					<button
						type="button"
						onclick={() => (regionPickerOpen = true)}
						class="text-xs text-primary underline underline-offset-2"
					>
						동네 설정하기
					</button>
				{/if}
			</div>

			{#if feed.length === 0}
				<!-- Empty state -->
				<div class="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-card py-12 text-center">
					<div class="text-3xl">🛍️</div>
					<div class="space-y-1">
						<p class="text-sm font-medium text-foreground">
							{#if currentRegion}
								{currentRegion}에 진행 중인 공구가 없어요
							{:else}
								진행 중인 공구가 없어요
							{/if}
						</p>
						<p class="text-xs text-muted-foreground">조금만 기다려보세요. 새 공구가 곧 열릴 거예요.</p>
					</div>
				</div>
			{:else}
				<ul class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each feed as item}
						<li>
							<a
								href="/g/{item.public_id}"
								class="block rounded-xl bg-card ring-1 ring-border overflow-hidden hover:ring-primary/30 transition-all active:scale-[0.99]"
							>
								<div class="relative">
									{#if item.image_url}
										<img src={item.image_url} alt={item.product_name} class="h-40 w-full object-cover" />
									{:else}
										<div class="flex h-32 w-full items-center justify-center bg-muted text-3xl">📦</div>
									{/if}
									{#if isClosingSoon(item.closes_at)}
										<span class="absolute left-2 top-2 rounded-full bg-destructive px-2 py-0.5 text-[10px] font-bold text-destructive-foreground shadow">
											마감 임박
										</span>
									{/if}
								</div>
								<div class="space-y-1 px-4 py-3.5">
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
											<span class="font-medium {isClosingSoon(item.closes_at) ? 'text-destructive' : 'text-primary/80'}">{timeUntil(item.closes_at)}</span>
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

<!-- Create group floating action button -->
<button
	type="button"
	onclick={handleCreateGroup}
	aria-label="공구 만들기"
	class="fixed bottom-20 right-4 z-40 flex h-14 items-center gap-2 rounded-full bg-primary px-5 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/30 transition-all hover:brightness-95 active:scale-95 md:bottom-8 md:right-8 md:h-12 md:px-4 md:text-[13px]"
>
	<IconPlus size={20} stroke={2.5} />
	공구 만들기
</button>

<!-- Region picker -->
{#if regionPickerOpen}
	<div
		class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
		onclick={(e) => { if (e.target === e.currentTarget) regionPickerOpen = false; }}
		onkeydown={(e) => { if (e.key === 'Escape') regionPickerOpen = false; }}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
	>
		<div class="w-full max-w-md rounded-t-2xl bg-background p-5 sm:rounded-2xl">
			<div class="mb-3 flex items-center justify-between">
				<h3 class="text-base font-bold text-foreground">동네 선택</h3>
				<button
					type="button"
					onclick={() => (regionPickerOpen = false)}
					class="text-xs text-muted-foreground hover:text-foreground"
				>
					닫기
				</button>
			</div>
			<p class="mb-3 text-xs text-muted-foreground">선택한 동네의 공동구매가 홈에 보입니다.</p>
			<input
				type="search"
				bind:value={regionSearch}
				placeholder="동네 검색 (예: 강남, 성남)"
				class="mb-3 h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
			/>
			<ul class="max-h-[60vh] space-y-1 overflow-y-auto">
				{#if filteredRegions.length === 0}
					<li class="px-3 py-4 text-center text-xs text-muted-foreground">검색 결과가 없습니다.</li>
				{/if}
				{#each filteredRegions as region}
					<li>
						<button
							type="button"
							disabled={savingRegion}
							onclick={() => selectRegion(region)}
							class="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted disabled:opacity-50 {region === currentRegion ? 'bg-primary/10 text-primary font-medium' : 'text-foreground'}"
						>
							{region}
							{#if region === currentRegion}
								<span class="text-xs">선택됨</span>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		</div>
	</div>
{/if}
