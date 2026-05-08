<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';

	type Group = {
		id: string;
		public_id: string;
		status: string;
		type: string;
		product_name: string;
		price: number;
		description?: string;
		image_url?: string;
		max_quantity?: number;
		remaining_qty?: number;
		min_quantity?: number;
		closes_at: string;
		closed_at?: string;
		pickup_slots: { id: string; label: string; start_at: string; end_at: string }[];
		created_at: string;
	};

	type OwnerOrderItem = {
		id: string;
		user_id: string;
		user_name: string;
		status: string;
		quantity: number;
		current_quantity: number;
		total_amount: number;
		current_amount: number;
		pickup_slot_label?: string;
		cancel_requested_at?: string;
		cancel_request_reason?: string;
		created_at: string;
		total_order_count: number;
		total_quantity_ordered: number;
		last_order_date: string;
		is_regular: boolean;
	};

	type OrderListData = {
		items: OwnerOrderItem[];
		total: number;
		pending_cancel_count: number;
	};

	let group = $state<Group | null>(null);
	let orderData = $state<OrderListData | null>(null);
	let loading = $state(true);
	let actionLoading = $state(false);
	let cancelActionLoading = $state<Record<string, boolean>>({});
	let error = $state('');

	const groupId = $derived($page.params.groupId);

	const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
		open: { label: '진행 중', variant: 'default' },
		closed: { label: '마감', variant: 'secondary' },
		pickup_ready: { label: '수령 가능', variant: 'outline' },
		completed: { label: '완료', variant: 'secondary' },
		cancelled: { label: '취소됨', variant: 'destructive' }
	};

	const cancelRequests = $derived(
		orderData?.items.filter((o) => o.cancel_requested_at != null) ?? []
	);

	onMount(loadData);

	async function loadData() {
		try {
			const [groupsResp, ordersResp] = await Promise.allSettled([
				api.get<{ items: Group[] }>(`/groups/my`),
				api.get<OrderListData>(`/groups/${groupId}/orders`)
			]);
			if (groupsResp.status === 'fulfilled') {
				group = groupsResp.value.items.find((g) => g.id === groupId) ?? null;
				if (!group) error = '공구를 찾을 수 없습니다';
			} else {
				error = '공구 정보를 불러올 수 없습니다';
			}
			if (ordersResp.status === 'fulfilled') {
				orderData = ordersResp.value;
			}
		} finally {
			loading = false;
		}
	}

	async function handleAction(action: string) {
		actionLoading = true;
		error = '';
		try {
			group = await api.post<Group>(`/groups/${groupId}/${action}`);
			await loadData();
			toast.success('처리되었습니다');
		} catch (e: unknown) {
			toast.error(e instanceof Error ? e.message : '작업에 실패했습니다');
		} finally {
			actionLoading = false;
		}
	}

	async function handleDelete() {
		if (!confirm('정말 삭제하시겠습니까?')) return;
		actionLoading = true;
		try {
			await api.delete(`/groups/${groupId}`);
			goto('/owner/groups');
		} catch (e: unknown) {
			toast.error(e instanceof Error ? e.message : '삭제에 실패했습니다');
			actionLoading = false;
		}
	}

	async function handleApproveCancel(orderId: string) {
		cancelActionLoading = { ...cancelActionLoading, [orderId]: true };
		try {
			await api.post(`/orders/${orderId}/approve-cancel`);
			await loadData();
			toast.success('취소가 승인되었습니다');
		} catch (e: unknown) {
			toast.error(e instanceof Error ? e.message : '취소 승인에 실패했습니다');
		} finally {
			const next = { ...cancelActionLoading };
			delete next[orderId];
			cancelActionLoading = next;
		}
	}

	async function handleRejectCancel(orderId: string) {
		cancelActionLoading = { ...cancelActionLoading, [orderId + '_reject']: true };
		try {
			await api.post(`/orders/${orderId}/reject-cancel`);
			await loadData();
			toast.success('취소가 거절되었습니다');
		} catch (e: unknown) {
			toast.error(e instanceof Error ? e.message : '취소 거절에 실패했습니다');
		} finally {
			const next = { ...cancelActionLoading };
			delete next[orderId + '_reject'];
			cancelActionLoading = next;
		}
	}

	function copyShareLink() {
		if (!group) return;
		navigator.clipboard.writeText(`${window.location.origin}/g/${group.public_id}`);
		toast.success('링크가 복사되었습니다!');
	}

	function formatPrice(n: number): string {
		return n.toLocaleString('ko-KR');
	}
</script>

<svelte:head>
	<title>{group?.product_name ?? '공구 상세'} - 모아오더</title>
</svelte:head>

<div class="mx-auto max-w-2xl space-y-5 px-5 pt-6 pb-10">
	{#if loading}
		<div class="space-y-3">
			<div class="h-8 w-48 animate-pulse rounded-lg bg-muted"></div>
			{#each [0, 1, 2] as _}
				<div class="h-24 animate-pulse rounded-2xl bg-muted"></div>
			{/each}
		</div>
	{:else if !group}
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-[14px] font-bold text-foreground">{error || '공구를 찾을 수 없어요'}</p>
			<button class="text-[13px] font-semibold text-primary underline-offset-2 hover:underline" onclick={() => goto('/owner/groups')}>
				목록으로
			</button>
		</div>
	{:else}
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<h1 class="text-[22px] font-bold leading-tight tracking-[-0.02em] text-foreground sm:text-[26px]">
				{group.product_name}
			</h1>
			<Badge variant={statusConfig[group.status]?.variant ?? 'secondary'} class="shrink-0 mt-1">
				{statusConfig[group.status]?.label ?? group.status}
			</Badge>
		</div>

		<!-- Image -->
		{#if group.image_url}
			<img src={group.image_url} alt={group.product_name} class="aspect-video w-full rounded-2xl object-cover" />
		{/if}

		<!-- Info card -->
		<div class="space-y-3 rounded-2xl bg-card px-5 py-5 ring-1 ring-border">
			<div class="flex items-baseline justify-between">
				<span class="text-[13px] text-muted-foreground">가격</span>
				<span class="text-[18px] font-bold tracking-[-0.02em] text-foreground">{formatPrice(group.price)}원</span>
			</div>
			<div class="flex justify-between text-[14px]">
				<span class="text-muted-foreground">타입</span>
				<span class="text-foreground">{{ reservation: '예약주문형', group_buy: '공동구매형', pickup: '픽업형' }[group.type]}</span>
			</div>
			<div class="flex justify-between text-[14px]">
				<span class="text-muted-foreground">마감 시간</span>
				<span class="text-foreground">{new Date(group.closes_at).toLocaleString('ko-KR')}</span>
			</div>
			{#if group.max_quantity}
				<div class="flex justify-between text-[14px]">
					<span class="text-muted-foreground">잔여/전체</span>
					<span class="text-foreground">{group.remaining_qty ?? 0} / {group.max_quantity}</span>
				</div>
			{/if}
			{#if group.min_quantity}
				<div class="flex justify-between text-[14px]">
					<span class="text-muted-foreground">최소 수량</span>
					<span class="text-foreground">{group.min_quantity}개</span>
				</div>
			{/if}
		</div>

		{#if group.description}
			<div class="rounded-2xl bg-card px-5 py-5 ring-1 ring-border">
				<p class="whitespace-pre-wrap text-[14px] leading-relaxed text-foreground">{group.description}</p>
			</div>
		{/if}

		<!-- Share link -->
		<div class="space-y-3 rounded-2xl bg-card px-5 py-5 ring-1 ring-border">
			<p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">공유 링크</p>
			<p class="break-all rounded-lg bg-muted px-3 py-2 font-mono text-[12px] text-foreground">{window.location.origin}/g/{group.public_id}</p>
			<Button variant="outline" class="w-full" onclick={copyShareLink}>
				<svg class="size-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
				</svg>
				링크 복사
			</Button>
		</div>

		<!-- Cancel requests -->
		{#if cancelRequests.length > 0}
			<div class="space-y-3">
				<h2 class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
					취소 요청 {cancelRequests.length}건
				</h2>
				{#each cancelRequests as order}
					<div class="space-y-3 rounded-2xl bg-amber-50 px-5 py-5 ring-1 ring-amber-100">
						<div class="flex items-center justify-between">
							<span class="text-[14px] font-bold text-foreground">{order.user_name}</span>
							<span class="text-[14px] text-muted-foreground">{order.current_quantity}개</span>
						</div>
						{#if order.cancel_request_reason}
							<p class="text-[13px] leading-relaxed text-foreground">사유: {order.cancel_request_reason}</p>
						{/if}
						<p class="text-[12px] text-muted-foreground">
							요청 {new Date(order.cancel_requested_at!).toLocaleString('ko-KR')}
						</p>
						<div class="flex gap-2 pt-1">
							<button
								onclick={() => handleApproveCancel(order.id)}
								disabled={cancelActionLoading[order.id]}
								class="flex-1 rounded-xl bg-destructive py-2.5 text-[13px] font-bold text-destructive-foreground transition hover:bg-destructive/90 disabled:opacity-50"
							>
								{cancelActionLoading[order.id] ? '처리중...' : '승인 (환불)'}
							</button>
							<button
								onclick={() => handleRejectCancel(order.id)}
								disabled={cancelActionLoading[order.id + '_reject']}
								class="flex-1 rounded-xl border border-border bg-background py-2.5 text-[13px] font-bold text-foreground transition hover:bg-muted disabled:opacity-50"
							>
								{cancelActionLoading[order.id + '_reject'] ? '처리중...' : '거절'}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Orders summary -->
		{#if orderData && orderData.items.length > 0}
			<div class="space-y-2.5">
				<div class="flex items-end justify-between">
					<h2 class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
						주문 현황 ({orderData.total}건)
					</h2>
					{#if group.status !== 'open'}
						<a href="/owner/groups/{groupId}/picking" class="text-[12px] font-semibold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
							피킹 리스트 →
						</a>
					{/if}
				</div>
				{#each orderData.items.slice(0, 5) as order}
					<div class="flex items-center justify-between gap-3 rounded-2xl bg-card px-5 py-3.5 ring-1 ring-border">
						<div class="flex min-w-0 items-center gap-2">
							<span class="truncate text-[14px] font-semibold text-foreground">{order.user_name}</span>
							{#if order.is_regular}
								<span class="shrink-0 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary">단골</span>
							{/if}
						</div>
						<div class="shrink-0 text-right">
							<span class="text-[14px] font-bold text-foreground">{order.current_quantity}개</span>
							<span class="ml-2 text-[12px] text-muted-foreground">{order.total_order_count}회 주문</span>
						</div>
					</div>
				{/each}
				{#if orderData.items.length > 5}
					<p class="pt-1 text-center text-[12px] text-muted-foreground">외 {orderData.items.length - 5}건</p>
				{/if}
			</div>
		{/if}

		<!-- Action buttons -->
		<div class="space-y-2.5 pt-2">
			{#if group.status === 'open'}
				<div class="flex gap-2.5">
					<Button variant="outline" class="flex-1" onclick={() => goto(`/owner/groups/${groupId}/edit`)}>수정</Button>
					<Button
						class="flex-1 border-0 bg-destructive/10 text-destructive hover:bg-destructive/20"
						onclick={() => handleAction('close')}
						disabled={actionLoading}
					>
						조기 마감
					</Button>
				</div>
				<Button
					variant="outline"
					class="w-full border-destructive/30 text-destructive hover:bg-destructive/5"
					onclick={handleDelete}
					disabled={actionLoading}
				>
					삭제
				</Button>
			{:else if group.status === 'closed'}
				<Button variant="outline" class="w-full" href="/owner/groups/{groupId}/picking">
					피킹 리스트 확인
				</Button>
				<Button class="w-full" onclick={() => handleAction('pickup-ready')} disabled={actionLoading}>
					수령 가능으로 변경
				</Button>
			{:else if group.status === 'pickup_ready'}
				<Button variant="outline" class="w-full" href="/owner/groups/{groupId}/picking">
					피킹 리스트 확인
				</Button>
				<Button class="w-full" href="/owner/groups/{groupId}/picking">
					공구 전체 완료
				</Button>
			{/if}
		</div>
	{/if}
</div>
