<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';

	type Group = {
		id: string;
		public_id: string;
		status: string;
		type: string;
		product_name: string;
		price: number;
		image_url?: string;
		remaining_qty?: number;
		max_quantity?: number;
		closes_at: string;
	};

	type PaginatedGroups = {
		items: Group[];
		total: number;
		page: number;
		limit: number;
	};

	let groups = $state<Group[]>([]);
	let total = $state(0);
	let loading = $state(true);
	let statusFilter = $state('');

	const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
		open: { label: '진행 중', variant: 'default' },
		closed: { label: '마감', variant: 'secondary' },
		pickup_ready: { label: '수령 가능', variant: 'outline' },
		completed: { label: '완료', variant: 'secondary' },
		cancelled: { label: '취소됨', variant: 'destructive' }
	};

	const filterTabs = [
		{ value: '', label: '전체' },
		{ value: 'open', label: '진행 중' },
		{ value: 'closed', label: '마감됨' },
		{ value: 'pickup_ready', label: '수령 가능' },
		{ value: 'completed', label: '완료' },
		{ value: 'cancelled', label: '취소' }
	];

	async function loadGroups() {
		loading = true;
		try {
			const query = statusFilter ? `?status=${statusFilter}` : '';
			const data = await api.get<PaginatedGroups>(`/groups/my${query}`);
			groups = data.items;
			total = data.total;
		} catch {
			groups = [];
		} finally {
			loading = false;
		}
	}

	function formatPrice(n: number): string {
		return n.toLocaleString('ko-KR');
	}

	onMount(loadGroups);

	$effect(() => {
		statusFilter;
		loadGroups();
	});
</script>

<svelte:head>
	<title>공구관리 - 모아오더</title>
</svelte:head>

<div class="mx-auto max-w-3xl space-y-5 px-5 pt-6 pb-8">
	<!-- Header -->
	<div class="flex items-end justify-between gap-3">
		<h1 class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[32px]">
			공구 관리
		</h1>
		<Button href="/owner/groups/create" size="sm">
			<svg class="size-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
			</svg>
			새 공구
		</Button>
	</div>

	<!-- Filter tabs -->
	<div class="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
		{#each filterTabs as tab}
			<button
				class="shrink-0 whitespace-nowrap rounded-full px-3.5 py-1.5 text-[13px] font-bold transition-colors {statusFilter === tab.value
					? 'bg-foreground text-background'
					: 'bg-muted text-muted-foreground hover:text-foreground'}"
				onclick={() => { statusFilter = tab.value; }}
			>
				{tab.label}
			</button>
		{/each}
	</div>

	{#if loading}
		<!-- Skeleton -->
		<div class="space-y-2.5">
			{#each [0, 1, 2, 3] as _}
				<div class="h-20 animate-pulse rounded-2xl bg-muted"></div>
			{/each}
		</div>
	{:else if groups.length === 0}
		<!-- Empty state -->
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">📦</div>
			<div class="space-y-1.5">
				<p class="text-[15px] font-bold text-foreground">
					{statusFilter ? '해당 상태의 공구가 없어요' : '아직 공구가 없어요'}
				</p>
				{#if !statusFilter}
					<p class="text-[13px] text-muted-foreground">첫 공구를 만들어 시작해보세요</p>
				{/if}
			</div>
			{#if !statusFilter}
				<Button href="/owner/groups/create" size="sm">새 공구 만들기</Button>
			{/if}
		</div>
	{:else}
		<div class="space-y-2.5">
			{#each groups as group}
				<a
					href="/owner/groups/{group.id}"
					class="flex items-center gap-4 rounded-2xl bg-card px-4 py-4 ring-1 ring-border transition-all hover:ring-primary/30 active:scale-[0.99]"
				>
					<!-- Thumbnail -->
					{#if group.image_url}
						<img src={group.image_url} alt="" class="h-14 w-14 shrink-0 rounded-xl object-cover" />
					{:else}
						<div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-muted text-xl">📦</div>
					{/if}

					<!-- Info -->
					<div class="min-w-0 flex-1">
						<div class="mb-1 flex items-center gap-2">
							<Badge variant={statusConfig[group.status]?.variant ?? 'secondary'} class="h-4 text-[10px]">
								{statusConfig[group.status]?.label ?? group.status}
							</Badge>
						</div>
						<p class="truncate text-[14px] font-bold text-foreground">{group.product_name}</p>
						<div class="mt-1 flex items-center gap-2 text-[12px] text-muted-foreground">
							<span class="font-semibold text-foreground">{formatPrice(group.price)}원</span>
							{#if group.max_quantity}
								<span>·</span>
								<span>잔여 {group.remaining_qty ?? 0}/{group.max_quantity}</span>
							{/if}
						</div>
					</div>

					<svg class="size-4 shrink-0 text-muted-foreground" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			{/each}
		</div>

		{#if total > groups.length}
			<p class="pt-1 text-center text-[12px] text-muted-foreground">총 {total}개 중 {groups.length}개 표시</p>
		{/if}
	{/if}
</div>
