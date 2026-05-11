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
		group_status: string;
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
	let pickupReadyLoading = $state(false);

	onMount(loadPickingList);

	async function setPickupReady() {
		pickupReadyLoading = true;
		try {
			await api.post(`/groups/${groupId}/pickup-ready`);
			await loadPickingList();
			toast.success('수령 가능 상태로 전환했어요. 고객에게 알림이 발송됩니다.');
		} catch (e: unknown) {
			toast.error(e instanceof Error ? e.message : '상태 변경에 실패했습니다');
		} finally {
			pickupReadyLoading = false;
		}
	}

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

<div class="mx-auto max-w-2xl space-y-5 px-5 pt-6 pb-28">
	{#if loading}
		<div class="space-y-3">
			<div class="h-8 w-48 animate-pulse rounded-lg bg-muted"></div>
			<div class="h-16 animate-pulse rounded-2xl bg-muted"></div>
			{#each [0, 1, 2, 3, 4] as _}
				<div class="h-16 animate-pulse rounded-2xl bg-muted"></div>
			{/each}
		</div>
	{:else if error && !data}
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-[14px] font-bold text-foreground">{error}</p>
			<button class="text-[13px] font-semibold text-primary underline-offset-2 hover:underline" onclick={loadPickingList}>
				다시 시도
			</button>
		</div>
	{:else if data}
		<!-- Header -->
		<div class="space-y-1.5">
			<h1 class="text-[22px] font-bold leading-tight tracking-[-0.02em] text-foreground sm:text-[26px]">
				{data.product_name}
			</h1>
			<p class="text-[13px] text-muted-foreground">
				총 수량 <span class="ml-1 font-bold text-foreground">{data.total_quantity}개</span>
			</p>
		</div>

		<!-- Stage banner: closed → pickup_ready transition needed -->
		{#if data.group_status === 'closed'}
			<div class="space-y-3 rounded-2xl bg-amber-50 px-5 py-4 ring-1 ring-amber-100">
				<div class="space-y-1">
					<p class="text-[14px] font-bold text-amber-900">아직 준비 단계예요</p>
					<p class="text-[13px] leading-relaxed text-amber-800/80">
						상품 준비가 끝났으면 수령 가능 상태로 전환하세요. 고객에게 알림이 발송되고, 그 다음부터 수령 처리를 시작할 수 있어요.
					</p>
				</div>
				<button
					type="button"
					onclick={setPickupReady}
					disabled={pickupReadyLoading}
					class="w-full rounded-xl bg-amber-600 px-4 py-2.5 text-[14px] font-bold text-white transition-colors hover:bg-amber-700 disabled:opacity-60"
				>
					{pickupReadyLoading ? '전환 중...' : '수령 가능으로 변경'}
				</button>
			</div>
		{:else if data.group_status === 'done'}
			<div class="rounded-2xl bg-muted/40 px-5 py-4 text-[13px] text-muted-foreground">
				공구가 완료되어 더 이상 수령 처리할 수 없어요. 기록만 확인할 수 있습니다.
			</div>
		{/if}

		<!-- Progress bar -->
		<div class="space-y-3 rounded-2xl bg-card px-5 py-5 ring-1 ring-border">
			<div class="flex items-center justify-between">
				<span class="text-[14px] font-bold text-foreground">수령 완료</span>
				<span class="text-[14px] font-bold {progress >= 100 ? 'text-emerald-600' : 'text-foreground'}">{pickedCount} / {totalCount}</span>
			</div>
			<div class="h-2.5 w-full overflow-hidden rounded-full bg-muted">
				<div
					class="h-full rounded-full transition-all duration-500 {progress >= 100 ? 'bg-emerald-500' : 'bg-primary'}"
					style="width: {progress}%"
				></div>
			</div>
			{#if progress >= 100}
				<p class="text-[12px] font-semibold text-emerald-600">전원 수령 완료!</p>
			{/if}
		</div>

		<!-- Search + filter -->
		<div class="flex gap-2">
			<div class="relative flex-1">
				<svg class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="주문자 검색"
					class="h-11 w-full rounded-xl border border-input bg-background pl-9 pr-3 text-[14px] placeholder:text-muted-foreground transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
				/>
			</div>
			<button
				onclick={() => (showOnlyUnpicked = !showOnlyUnpicked)}
				class="shrink-0 rounded-xl border px-4 text-[13px] font-bold transition-colors {showOnlyUnpicked
					? 'border-foreground bg-foreground text-background'
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
			<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
				<div class="text-4xl">📭</div>
				<p class="text-[14px] font-bold text-foreground">해당하는 주문이 없어요</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Fixed bottom CTA -->
{#if data && data.group_status === 'pickup_ready'}
	<div class="fixed bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur-sm px-5 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] md:left-60">
		<Button class="w-full max-w-2xl" size="lg" onclick={completeGroup} disabled={completeLoading}>
			{completeLoading ? '처리 중...' : '공구 전체 완료'}
		</Button>
	</div>
{/if}

{#snippet PickingCard(item: PickingItem)}
	<div class="flex items-center justify-between gap-3 rounded-2xl bg-card px-5 py-4 ring-1 ring-border transition-all {item.is_picked_up ? 'opacity-50' : ''}">
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<span class="truncate text-[14px] font-bold text-foreground">{item.user_name}</span>
				{#if item.is_picked_up}
					<span class="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 ring-1 ring-emerald-100">수령완료</span>
				{/if}
			</div>
			<div class="mt-1 text-[12px] text-muted-foreground">
				수량 <span class="font-bold text-foreground">{item.quantity}개</span>
				{#if item.pickup_slot_label}
					<span class="ml-2">· {item.pickup_slot_label}</span>
				{/if}
			</div>
		</div>
		{#if !item.is_picked_up && data?.group_status === 'pickup_ready'}
			<button
				onclick={() => markPickedUp(item.order_id)}
				disabled={actionLoading[item.order_id]}
				class="shrink-0 rounded-xl bg-primary/5 px-4 py-2 text-[13px] font-bold text-primary ring-1 ring-primary/20 transition-colors hover:bg-primary/10 disabled:opacity-50"
			>
				{actionLoading[item.order_id] ? '...' : '수령'}
			</button>
		{/if}
	</div>
{/snippet}
