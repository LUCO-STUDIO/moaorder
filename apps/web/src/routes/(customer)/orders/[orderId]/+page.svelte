<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { api, ApiRequestError } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';

	interface OrderEvent {
		id: string;
		event_type: string;
		actor_type: string | null;
		metadata: Record<string, unknown> | null;
		created_at: string;
	}

	interface PickupSlot {
		id: string;
		label: string;
		start_at: string;
		end_at: string;
	}

	interface OrderDetail {
		id: string;
		group_id: string;
		store_id: string;
		status: string;
		status_label: string;
		status_sub: string;
		product_name: string;
		store_name: string;
		quantity: number;
		total_amount: number;
		current_quantity: number;
		current_amount: number;
		payment_id: string | null;
		paid_at: string | null;
		pickup_slot: PickupSlot | null;
		cancel_requested_at: string | null;
		events: OrderEvent[];
		group_closes_at: string;
		group_status: string;
		created_at: string;
		updated_at: string;
	}

	let order: OrderDetail | null = $state(null);
	let loading = $state(true);
	let error = $state('');

	let showReduceSheet = $state(false);
	let newQuantity = $state(1);
	let showCancelSheet = $state(false);
	let showCancelRequestSheet = $state(false);
	let cancelReason = $state('');
	let actionLoading = $state(false);

	const eventLabels: Record<string, string> = {
		payment_completed: '결제 완료',
		quantity_reduced: '수량 변경',
		order_cancelled: '주문 취소',
		cancel_requested: '취소 요청',
		status_changed: '상태 변경'
	};

	const statusBadge: Record<string, string> = {
		paid: 'bg-primary/10 text-primary',
		confirmed: 'bg-amber-50 text-amber-700',
		pickup_ready: 'bg-emerald-50 text-emerald-700',
		cancelled: 'bg-muted text-muted-foreground'
	};

	function isPreDeadline(o: OrderDetail): boolean {
		return (
			o.status === 'paid' &&
			o.group_status === 'open' &&
			new Date(o.group_closes_at) > new Date()
		);
	}

	function canCancelRequest(o: OrderDetail): boolean {
		return o.status === 'confirmed' && o.cancel_requested_at === null;
	}

	async function loadOrder() {
		const orderId = $page.params.orderId;
		loading = true;
		error = '';
		try {
			order = await api.get<OrderDetail>(`/orders/${orderId}`);
			if (order) newQuantity = Math.max(1, order.current_quantity - 1);
		} catch (e) {
			error = e instanceof ApiRequestError ? e.message : '주문 정보를 불러올 수 없습니다';
		} finally {
			loading = false;
		}
	}

	async function handleReduce() {
		if (!order) return;
		actionLoading = true;
		try {
			await api.post(`/orders/${order.id}/reduce`, { quantity_after: newQuantity });
			showReduceSheet = false;
			await loadOrder();
			toast.success('수량이 변경되었습니다');
		} catch (e) {
			toast.error(e instanceof ApiRequestError ? e.message : '수량 변경에 실패했습니다');
		} finally {
			actionLoading = false;
		}
	}

	async function handleCancel() {
		if (!order) return;
		actionLoading = true;
		try {
			await api.post(`/orders/${order.id}/cancel`);
			showCancelSheet = false;
			await loadOrder();
			toast.success('주문이 취소되었습니다');
		} catch (e) {
			toast.error(e instanceof ApiRequestError ? e.message : '취소에 실패했습니다');
		} finally {
			actionLoading = false;
		}
	}

	async function handleCancelRequest() {
		if (!order) return;
		actionLoading = true;
		try {
			await api.post(`/orders/${order.id}/cancel-request`, { reason: cancelReason || null });
			showCancelRequestSheet = false;
			await loadOrder();
			toast.success('취소 요청이 접수되었습니다');
		} catch (e) {
			toast.error(e instanceof ApiRequestError ? e.message : '취소 요청에 실패했습니다');
		} finally {
			actionLoading = false;
		}
	}

	onMount(loadOrder);
</script>

<svelte:head>
	<title>주문 상세 - 모아오더</title>
</svelte:head>

<!-- Page header -->
<div class="sticky top-0 z-10 flex items-center h-14 px-4 border-b border-border bg-background/95 backdrop-blur-sm">
	<button aria-label="뒤로 가기" onclick={() => history.back()} class="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted transition-colors -ml-2">
		<svg class="size-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
		</svg>
	</button>
	<h1 class="ml-2 text-base font-semibold text-foreground">주문 상세</h1>
</div>

<div class="space-y-3 px-5 py-5">
	{#if loading}
		<!-- Skeleton -->
		<div class="space-y-3">
			<div class="h-32 animate-pulse rounded-2xl bg-muted"></div>
			<div class="h-24 animate-pulse rounded-2xl bg-muted"></div>
			<div class="h-40 animate-pulse rounded-2xl bg-muted"></div>
		</div>
	{:else if error}
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">⚠️</div>
			<div class="space-y-1.5">
				<p class="text-[15px] font-bold text-foreground">{error}</p>
				<button class="text-[13px] font-semibold text-primary underline-offset-2 hover:underline" onclick={loadOrder}>
					다시 시도
				</button>
			</div>
		</div>
	{:else if order}
		<!-- Pickup ready banner -->
		{#if order.status === 'pickup_ready'}
			<div class="flex items-center gap-3 rounded-2xl bg-emerald-50 px-5 py-4 ring-1 ring-emerald-100">
				<span class="text-2xl">🎁</span>
				<p class="text-[14px] font-bold text-emerald-800">수령 가능합니다. 매장에서 수령해주세요.</p>
			</div>
		{/if}

		<!-- Order summary -->
		<section class="space-y-4 rounded-2xl bg-card px-5 py-5 ring-1 ring-border">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<p class="text-[12px] text-muted-foreground">{order.store_name}</p>
					<p class="mt-1 text-[16px] font-bold text-foreground">{order.product_name}</p>
				</div>
				<span class="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold {statusBadge[order.status] ?? 'bg-muted text-muted-foreground'}">
					{order.status_label}
				</span>
			</div>

			{#if order.status_sub}
				<p class="text-[12px] text-muted-foreground">{order.status_sub}</p>
			{/if}

			<div class="space-y-2.5 border-t border-border pt-4">
				<div class="flex justify-between text-[14px]">
					<span class="text-muted-foreground">수량</span>
					<span class="text-foreground">
						{order.current_quantity}개
						{#if order.current_quantity !== order.quantity}
							<span class="ml-1 text-[12px] text-muted-foreground">(최초 {order.quantity}개)</span>
						{/if}
					</span>
				</div>
				<div class="flex items-baseline justify-between">
					<span class="text-[14px] font-bold text-foreground">결제 금액</span>
					<span class="text-[20px] font-bold tracking-[-0.02em] text-foreground">{order.current_amount.toLocaleString()}원</span>
				</div>
				{#if order.paid_at}
					<div class="flex justify-between text-[13px]">
						<span class="text-muted-foreground">결제일</span>
						<span class="text-foreground">{new Date(order.paid_at).toLocaleDateString('ko-KR')}</span>
					</div>
				{/if}
			</div>
		</section>

		<!-- Pickup slot -->
		{#if order.pickup_slot}
			<section class="rounded-2xl bg-card px-5 py-5 ring-1 ring-border">
				<h2 class="mb-2.5 text-[14px] font-bold text-foreground">픽업 시간대</h2>
				<p class="text-[14px] font-semibold text-foreground">{order.pickup_slot.label}</p>
				<p class="mt-1 text-[12px] text-muted-foreground">
					{new Date(order.pickup_slot.start_at).toLocaleString('ko-KR', {
						month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
					})} ~
					{new Date(order.pickup_slot.end_at).toLocaleString('ko-KR', {
						hour: '2-digit', minute: '2-digit'
					})}
				</p>
			</section>
		{/if}

		<!-- Timeline -->
		{#if order.events.length > 0}
			<section class="rounded-2xl bg-card px-5 py-5 ring-1 ring-border">
				<h2 class="mb-5 text-[14px] font-bold text-foreground">주문 히스토리</h2>
				<ol class="relative ml-2 space-y-4 border-l-2 border-border">
					{#each order.events as event, i}
						<li class="relative pl-5">
							<span class="absolute -left-[9px] top-1 h-3.5 w-3.5 rounded-full border-2 border-background {i === 0 ? 'bg-primary' : 'bg-border'}"></span>
							<p class="text-[13px] font-semibold text-foreground">
								{eventLabels[event.event_type] ?? event.event_type}
							</p>
							<time class="text-[12px] text-muted-foreground">
								{new Date(event.created_at).toLocaleString('ko-KR', {
									month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
								})}
							</time>
						</li>
					{/each}
				</ol>
			</section>
		{/if}

		<!-- Quantity increase hint -->
		{#if isPreDeadline(order)}
			<p class="text-center text-[12px] text-muted-foreground">
				수량을 늘리려면 해당 공구에서 새로 주문해주세요
			</p>
		{/if}

		<!-- Action buttons -->
		{#if isPreDeadline(order)}
			<div class="flex gap-3 pt-1">
				<Button
					variant="outline"
					class="flex-1"
					onclick={() => { showReduceSheet = true; }}
				>
					수량 줄이기
				</Button>
				<Button
					variant="destructive"
					class="flex-1 bg-destructive/10 text-destructive hover:bg-destructive/20"
					onclick={() => { showCancelSheet = true; }}
				>
					전체 취소
				</Button>
			</div>
		{:else if canCancelRequest(order)}
			<div class="space-y-2 pt-1">
				<Button
					variant="outline"
					class="w-full"
					onclick={() => { showCancelRequestSheet = true; }}
				>
					취소 요청하기
				</Button>
				<p class="text-center text-[12px] text-muted-foreground">취소 요청은 사장님 승인 후 처리됩니다</p>
			</div>
		{:else if order.cancel_requested_at}
			<div class="rounded-2xl bg-amber-50 px-5 py-4 text-center text-[13px] font-semibold text-amber-800 ring-1 ring-amber-100">
				취소 요청이 접수되었습니다. 사장님 확인 중입니다.
			</div>
		{/if}
	{/if}
</div>

<!-- Reduce quantity bottom sheet -->
{#if showReduceSheet && order}
	<div
		class="fixed inset-0 z-50 flex items-end"
		role="dialog"
		aria-modal="true"
	>
		<button
			class="absolute inset-0 bg-black/50"
			onclick={() => (showReduceSheet = false)}
			aria-label="닫기"
		></button>
		<div class="relative w-full rounded-t-2xl bg-background px-5 py-6 space-y-5">
			<div class="mx-auto w-10 h-1 rounded-full bg-border"></div>
			<h2 class="text-base font-bold text-foreground">수량 줄이기</h2>
			<p class="text-sm text-muted-foreground">
				현재 수량: <strong class="text-foreground">{order.current_quantity}개</strong>
			</p>
			<div class="flex items-center justify-center gap-6">
				<button
					class="flex h-11 w-11 items-center justify-center rounded-full border-2 border-border text-xl font-bold hover:border-primary hover:text-primary transition-colors disabled:opacity-30"
					onclick={() => (newQuantity = Math.max(1, newQuantity - 1))}
					disabled={newQuantity <= 1}
				>
					−
				</button>
				<span class="w-10 text-center text-2xl font-bold tabular-nums">{newQuantity}</span>
				<button
					class="flex h-11 w-11 items-center justify-center rounded-full border-2 border-border text-xl font-bold hover:border-primary hover:text-primary transition-colors disabled:opacity-30"
					onclick={() => (newQuantity = Math.min(order!.current_quantity - 1, newQuantity + 1))}
					disabled={newQuantity >= order.current_quantity - 1}
				>
					+
				</button>
			</div>
			<p class="text-sm text-center text-primary font-semibold">
				환불 예정: ₩{((order.current_quantity - newQuantity) * (order.current_amount / order.current_quantity)).toLocaleString()}
			</p>
			<div class="flex gap-3">
				<Button variant="outline" class="flex-1" onclick={() => (showReduceSheet = false)} disabled={actionLoading}>
					취소
				</Button>
				<Button class="flex-1" onclick={handleReduce} disabled={actionLoading}>
					{actionLoading ? '처리 중...' : '수량 변경'}
				</Button>
			</div>
		</div>
	</div>
{/if}

<!-- Cancel confirm bottom sheet -->
{#if showCancelSheet && order}
	<div
		class="fixed inset-0 z-50 flex items-end"
		role="dialog"
		aria-modal="true"
	>
		<button
			class="absolute inset-0 bg-black/50"
			onclick={() => (showCancelSheet = false)}
			aria-label="닫기"
		></button>
		<div class="relative w-full rounded-t-2xl bg-background px-5 py-6 space-y-4">
			<div class="mx-auto w-10 h-1 rounded-full bg-border"></div>
			<h2 class="text-base font-bold text-foreground">주문을 취소할까요?</h2>
			<p class="text-sm text-muted-foreground">
				결제 금액 <strong class="text-foreground">₩{order.current_amount.toLocaleString()}</strong> 이 전액 환불됩니다.
			</p>
			<div class="flex gap-3">
				<Button variant="outline" class="flex-1" onclick={() => (showCancelSheet = false)} disabled={actionLoading}>
					돌아가기
				</Button>
				<Button
					class="flex-1 bg-destructive hover:bg-destructive/90 text-destructive-foreground"
					onclick={handleCancel}
					disabled={actionLoading}
				>
					{actionLoading ? '처리 중...' : '취소 확인'}
				</Button>
			</div>
		</div>
	</div>
{/if}

<!-- Cancel request bottom sheet -->
{#if showCancelRequestSheet && order}
	<div
		class="fixed inset-0 z-50 flex items-end"
		role="dialog"
		aria-modal="true"
	>
		<button
			class="absolute inset-0 bg-black/50"
			onclick={() => (showCancelRequestSheet = false)}
			aria-label="닫기"
		></button>
		<div class="relative w-full rounded-t-2xl bg-background px-5 py-6 space-y-4">
			<div class="mx-auto w-10 h-1 rounded-full bg-border"></div>
			<h2 class="text-base font-bold text-foreground">취소 요청</h2>
			<p class="text-sm text-muted-foreground">사장님 승인 후 환불이 진행됩니다.</p>
			<div class="space-y-1.5">
				<label class="text-xs font-medium text-foreground" for="cancel-reason">
					취소 사유 <span class="text-muted-foreground">(선택)</span>
				</label>
				<textarea
					id="cancel-reason"
					bind:value={cancelReason}
					rows="3"
					placeholder="취소 사유를 입력해주세요"
					class="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none resize-none transition-colors"
				></textarea>
			</div>
			<div class="flex gap-3">
				<Button variant="outline" class="flex-1" onclick={() => (showCancelRequestSheet = false)} disabled={actionLoading}>
					취소
				</Button>
				<Button class="flex-1" onclick={handleCancelRequest} disabled={actionLoading}>
					{actionLoading ? '처리 중...' : '요청 접수'}
				</Button>
			</div>
		</div>
	</div>
{/if}
