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

<div class="px-5 pt-6 pb-8 space-y-5 max-w-3xl">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold text-foreground">공구관리</h1>
		<Button href="/owner/groups/create" size="sm">
			<svg class="size-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
			</svg>
			새 공구
		</Button>
	</div>

	<!-- Filter tabs -->
	<div class="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
		{#each filterTabs as tab}
			<button
				class="shrink-0 rounded-full px-3.5 py-1.5 text-sm font-medium whitespace-nowrap transition-colors {statusFilter === tab.value
					? 'bg-primary text-primary-foreground'
					: 'bg-muted text-muted-foreground hover:text-foreground'}"
				onclick={() => { statusFilter = tab.value; }}
			>
				{tab.label}
			</button>
		{/each}
	</div>

	{#if loading}
		<!-- Skeleton -->
		{#each [0, 1, 2, 3] as _}
			<div class="rounded-xl bg-muted animate-pulse h-20"></div>
		{/each}
	{:else if groups.length === 0}
		<!-- Empty state -->
		<div class="flex flex-col items-center gap-4 rounded-xl border border-dashed border-border bg-card py-14 text-center">
			<div class="text-3xl">📦</div>
			<div class="space-y-1">
				<p class="text-sm font-semibold text-foreground">
					{statusFilter ? '해당 상태의 공구가 없습니다' : '등록된 공구가 없습니다'}
				</p>
				{#if !statusFilter}
					<p class="text-xs text-muted-foreground">새 공구를 만들어보세요!</p>
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
					class="flex items-center gap-3.5 rounded-xl bg-card ring-1 ring-border px-4 py-3.5 hover:ring-primary/30 transition-all active:scale-[0.99]"
				>
					<!-- Thumbnail -->
					{#if group.image_url}
						<img src={group.image_url} alt="" class="h-14 w-14 rounded-lg object-cover shrink-0" />
					{:else}
						<div class="h-14 w-14 rounded-lg bg-muted flex items-center justify-center text-xl shrink-0">📦</div>
					{/if}

					<!-- Info -->
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-0.5">
							<Badge variant={statusConfig[group.status]?.variant ?? 'secondary'} class="text-[10px] h-4">
								{statusConfig[group.status]?.label ?? group.status}
							</Badge>
						</div>
						<p class="text-sm font-semibold text-foreground truncate">{group.product_name}</p>
						<div class="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
							<span>{formatPrice(group.price)}원</span>
							{#if group.max_quantity}
								<span>·</span>
								<span>잔여 {group.remaining_qty ?? 0}/{group.max_quantity}</span>
							{/if}
						</div>
					</div>

					<svg class="size-4 text-muted-foreground shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			{/each}
		</div>

		{#if total > groups.length}
			<p class="text-center text-xs text-muted-foreground pt-1">총 {total}개 중 {groups.length}개 표시</p>
		{/if}
	{/if}
</div>
