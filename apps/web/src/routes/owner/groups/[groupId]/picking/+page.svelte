<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';

	type PickingItem = {
		order_id: string;
		user_name: string;
		quantity: number;
		pickup_slot_label?: string;
		pickup_slot_start_at?: string;
		is_picked_up: boolean;
	};

	type PickingSlotGroup = {
		slot_label: string;
		slot_start_at?: string;
		items: PickingItem[];
	};

	type PickingList = {
		group_id: string;
		product_name: string;
		total_quantity: number;
		items: PickingItem[];
		slot_groups: PickingSlotGroup[];
	};

	const groupId = $derived($page.params.groupId);

	let data = $state<PickingList | null>(null);
	let loading = $state(true);
	let error = $state('');
	let actionLoading = $state<Record<string, boolean>>({});
	let showOnlyUnpicked = $state(false);
	let searchQuery = $state('');
	let completeLoading = $state(false);

	onMount(loadPickingList);

	async function loadPickingList() {
		try {
			data = await api.get<PickingList>(`/groups/${groupId}/picking-list`);
		} catch {
			error = '피킹 리스트를 불러올 수 없습니다';
		} finally {
			loading = false;
		}
	}

	async function markPickedUp(orderId: string) {
		actionLoading = { ...actionLoading, [orderId]: true };
		try {
			await api.post(`/orders/${orderId}/mark-picked-up`);
			await loadPickingList();
			toast.success('수령 처리되었습니다');
		} catch (e: unknown) {
			toast.error(e instanceof Error ? e.message : '수령 처리에 실패했습니다');
		} finally {
			const next = { ...actionLoading };
			delete next[orderId];
			actionLoading = next;
		}
	}

	async function completeGroup() {
		if (!confirm('공구를 전체 완료 처리하시겠습니까?\n미수령 주문은 미수령 처리됩니다.')) return;
		completeLoading = true;
		try {
			await api.post(`/groups/${groupId}/complete`);
			toast.success('공구가 완료 처리되었습니다');
			window.location.href = `/owner/groups/${groupId}`;
		} catch (e: unknown) {
			toast.error(e instanceof Error ? e.message : '완료 처리에 실패했습니다');
			completeLoading = false;
		}
	}

	const filteredItems = $derived.by(() => {
		if (!data) return [];
		let items = data.items;
		if (showOnlyUnpicked) items = items.filter((i) => !i.is_picked_up);
		if (searchQuery.trim()) {
			const q = searchQuery.trim().toLowerCase();
			items = items.filter((i) => i.user_name.toLowerCase().includes(q));
		}
		return items;
	});

	const pickedCount = $derived(data?.items.filter((i) => i.is_picked_up).length ?? 0);
	const totalCount = $derived(data?.items.length ?? 0);
	const progress = $derived(totalCount > 0 ? (pickedCount / totalCount) * 100 : 0);
</script>

<svelte:head>
	<title>피킹 리스트 - 모아오더</title>
</svelte:head>

<div class="px-5 pt-6 pb-28 max-w-2xl space-y-5">
	{#if loading}
		<div class="space-y-3">
			<div class="h-8 w-48 bg-muted animate-pulse rounded-lg"></div>
			<div class="h-16 bg-muted animate-pulse rounded-xl"></div>
			{#each [0, 1, 2, 3, 4] as _}
				<div class="h-16 bg-muted animate-pulse rounded-xl"></div>
			{/each}
		</div>
	{:else if error && !data}
		<div class="flex flex-col items-center gap-3 py-16 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-sm text-foreground">{error}</p>
			<button class="text-sm text-primary underline underline-offset-2" onclick={loadPickingList}>
				다시 시도
			</button>
		</div>
	{:else if data}
		<!-- Header -->
		<div class="space-y-0.5">
			<h1 class="text-xl font-bold text-foreground">{data.product_name}</h1>
			<p class="text-sm text-muted-foreground">
				총 수량: <span class="font-semibold text-primary">{data.total_quantity}개</span>
			</p>
		</div>

		<!-- Progress bar -->
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-2.5">
			<div class="flex items-center justify-between text-sm">
				<span class="text-muted-foreground font-medium">수령 완료</span>
				<span class="font-bold text-foreground">{pickedCount} / {totalCount}</span>
			</div>
			<div class="h-2.5 w-full rounded-full bg-muted overflow-hidden">
				<div
					class="h-full rounded-full transition-all duration-500 {progress >= 100 ? 'bg-green-500' : 'bg-primary'}"
					style="width: {progress}%"
				></div>
			</div>
			{#if progress >= 100}
				<p class="text-xs text-green-600 font-medium">전원 수령 완료!</p>
			{/if}
		</div>

		<!-- Search + filter -->
		<div class="flex gap-2">
			<div class="relative flex-1">
				<svg class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="주문자 검색..."
					class="w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-colors"
				/>
			</div>
			<button
				onclick={() => (showOnlyUnpicked = !showOnlyUnpicked)}
				class="shrink-0 rounded-xl border px-3.5 py-2 text-sm font-medium transition-colors {showOnlyUnpicked
					? 'bg-primary text-primary-foreground border-primary'
					: 'border-border text-muted-foreground hover:text-foreground'}"
			>
				미수령만
			</button>
		</div>

		<!-- Slot groups (pickup type) -->
		{#if data.slot_groups.length > 0}
			{#each data.slot_groups as group}
				{@const groupItems = group.items.filter((item) => {
					if (showOnlyUnpicked && item.is_picked_up) return false;
					if (searchQuery.trim() && !item.user_name.toLowerCase().includes(searchQuery.trim().toLowerCase())) return false;
					return true;
				})}
				{#if groupItems.length > 0}
					<div class="space-y-2.5">
						<div class="flex items-center gap-2">
							<span class="text-sm font-semibold text-foreground">{group.slot_label}</span>
							{#if group.slot_start_at}
								<span class="text-xs text-muted-foreground">
									{new Date(group.slot_start_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
								</span>
							{/if}
						</div>
						{#each groupItems as item}
							{@render PickingCard(item)}
						{/each}
					</div>
				{/if}
			{/each}
		{:else}
			<!-- Flat list -->
			{#each filteredItems as item}
				{@render PickingCard(item)}
			{/each}
		{/if}

		{#if filteredItems.length === 0 && data.slot_groups.length === 0}
			<div class="flex flex-col items-center gap-2 py-12 text-center">
				<p class="text-sm text-muted-foreground">해당하는 주문이 없습니다</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Fixed bottom CTA -->
{#if data}
	<div class="fixed bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur-sm px-5 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] md:left-60">
		<Button class="w-full max-w-2xl" size="lg" onclick={completeGroup} disabled={completeLoading}>
			{completeLoading ? '처리 중...' : '공구 전체 완료'}
		</Button>
	</div>
{/if}

{#snippet PickingCard(item: PickingItem)}
	<div class="flex items-center justify-between gap-3 rounded-xl bg-card ring-1 ring-border px-4 py-3.5 transition-all {item.is_picked_up ? 'opacity-50' : ''}">
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2">
				<span class="text-sm font-semibold text-foreground truncate">{item.user_name}</span>
				{#if item.is_picked_up}
					<span class="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700">수령완료</span>
				{/if}
			</div>
			<div class="text-xs text-muted-foreground mt-0.5">
				수량 <span class="font-semibold text-foreground">{item.quantity}개</span>
				{#if item.pickup_slot_label}
					<span class="ml-2">· {item.pickup_slot_label}</span>
				{/if}
			</div>
		</div>
		{#if !item.is_picked_up}
			<button
				onclick={() => markPickedUp(item.order_id)}
				disabled={actionLoading[item.order_id]}
				class="shrink-0 rounded-lg border-2 border-primary/50 text-primary px-3.5 py-1.5 text-sm font-semibold hover:bg-primary/5 disabled:opacity-50 transition-colors"
			>
				{actionLoading[item.order_id] ? '...' : '수령'}
			</button>
		{/if}
	</div>
{/snippet}
