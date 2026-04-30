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

<div class="px-5 pt-6 pb-10 max-w-2xl space-y-5">
	{#if loading}
		<div class="space-y-3">
			<div class="h-8 w-48 bg-muted animate-pulse rounded-lg"></div>
			{#each [0, 1, 2] as _}
				<div class="h-24 bg-muted animate-pulse rounded-xl"></div>
			{/each}
		</div>
	{:else if !group}
		<div class="flex flex-col items-center gap-3 py-16 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-sm text-foreground">{error || '공구를 찾을 수 없습니다'}</p>
			<button class="text-sm text-primary underline underline-offset-2" onclick={() => goto('/owner/groups')}>
				목록으로
			</button>
		</div>
	{:else}
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<h1 class="text-xl font-bold text-foreground leading-snug">{group.product_name}</h1>
			<Badge variant={statusConfig[group.status]?.variant ?? 'secondary'}>
				{statusConfig[group.status]?.label ?? group.status}
			</Badge>
		</div>

		<!-- Image -->
		{#if group.image_url}
			<img src={group.image_url} alt={group.product_name} class="w-full aspect-video object-cover rounded-xl" />
		{/if}

		<!-- Info card -->
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-2.5 text-sm">
			<div class="flex justify-between">
				<span class="text-muted-foreground">가격</span>
				<span class="font-semibold text-foreground">{formatPrice(group.price)}원</span>
			</div>
			<div class="flex justify-between">
				<span class="text-muted-foreground">타입</span>
				<span class="text-foreground">{{ reservation: '예약주문형', group_buy: '공동구매형', pickup: '픽업형' }[group.type]}</span>
			</div>
			<div class="flex justify-between">
				<span class="text-muted-foreground">마감 시간</span>
				<span class="text-foreground">{new Date(group.closes_at).toLocaleString('ko-KR')}</span>
			</div>
			{#if group.max_quantity}
				<div class="flex justify-between">
					<span class="text-muted-foreground">잔여/전체</span>
					<span class="text-foreground">{group.remaining_qty ?? 0} / {group.max_quantity}</span>
				</div>
			{/if}
			{#if group.min_quantity}
				<div class="flex justify-between">
					<span class="text-muted-foreground">최소 수량</span>
					<span class="text-foreground">{group.min_quantity}개</span>
				</div>
			{/if}
		</div>

		{#if group.description}
			<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4">
				<p class="text-sm text-muted-foreground whitespace-pre-wrap">{group.description}</p>
			</div>
		{/if}

		<!-- Share link -->
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-2.5">
			<p class="text-xs font-medium text-muted-foreground">공유 링크</p>
			<p class="text-sm font-mono break-all text-primary">{window.location.origin}/g/{group.public_id}</p>
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
				<h2 class="text-sm font-semibold text-foreground">취소 요청 {cancelRequests.length}건</h2>
				{#each cancelRequests as order}
					<div class="rounded-xl bg-amber-50 border border-amber-200 px-4 py-4 space-y-3">
						<div class="flex items-center justify-between">
							<span class="text-sm font-semibold text-foreground">{order.user_name}</span>
							<span class="text-sm text-muted-foreground">{order.current_quantity}개</span>
						</div>
						{#if order.cancel_request_reason}
							<p class="text-sm text-muted-foreground">사유: {order.cancel_request_reason}</p>
						{/if}
						<p class="text-xs text-muted-foreground">
							요청: {new Date(order.cancel_requested_at!).toLocaleString('ko-KR')}
						</p>
						<div class="flex gap-2">
							<button
								onclick={() => handleApproveCancel(order.id)}
								disabled={cancelActionLoading[order.id]}
								class="flex-1 rounded-xl bg-destructive py-2.5 text-sm font-semibold text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 transition"
							>
								{cancelActionLoading[order.id] ? '처리중...' : '승인 (환불)'}
							</button>
							<button
								onclick={() => handleRejectCancel(order.id)}
								disabled={cancelActionLoading[order.id + '_reject']}
								class="flex-1 rounded-xl border border-border text-foreground py-2.5 text-sm font-medium hover:bg-muted disabled:opacity-50 transition"
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
				<div class="flex items-center justify-between">
					<h2 class="text-sm font-semibold text-foreground">주문 현황 ({orderData.total}건)</h2>
					{#if group.status !== 'open'}
						<a href="/owner/groups/{groupId}/picking" class="text-xs text-primary hover:underline underline-offset-2">
							피킹 리스트 →
						</a>
					{/if}
				</div>
				{#each orderData.items.slice(0, 5) as order}
					<div class="flex items-center justify-between rounded-xl bg-card ring-1 ring-border px-4 py-3">
						<div class="flex items-center gap-2">
							<span class="text-sm font-medium text-foreground">{order.user_name}</span>
							{#if order.is_regular}
								<span class="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-medium">단골</span>
							{/if}
						</div>
						<div class="text-right text-sm">
							<span class="text-foreground font-medium">{order.current_quantity}개</span>
							<span class="text-muted-foreground ml-2 text-xs">{order.total_order_count}회 주문</span>
						</div>
					</div>
				{/each}
				{#if orderData.items.length > 5}
					<p class="text-xs text-center text-muted-foreground">외 {orderData.items.length - 5}건</p>
				{/if}
			</div>
		{/if}

		<!-- Action buttons -->
		<div class="space-y-2.5">
			{#if group.status === 'open'}
				<div class="flex gap-2.5">
					<Button variant="outline" class="flex-1" onclick={() => goto(`/owner/groups/${groupId}/edit`)}>수정</Button>
					<Button
						class="flex-1 bg-destructive/10 text-destructive hover:bg-destructive/20 border-0"
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
