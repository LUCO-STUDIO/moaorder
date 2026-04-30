<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';

	let { data } = $props();
	let group = $derived(data.group);

	let now = $state(Date.now());

	$effect(() => {
		const timer = setInterval(() => { now = Date.now(); }, 1000);
		return () => clearInterval(timer);
	});

	let closesAtMs = $derived(new Date(group.closes_at).getTime());
	let remainingMs = $derived(Math.max(0, closesAtMs - now));
	let isExpired = $derived(remainingMs <= 0);
	let isClosed = $derived(group.status !== 'open');
	let isSoldOut = $derived(group.remaining_qty !== null && group.remaining_qty <= 0);
	let canOrder = $derived(!isClosed && !isExpired && !isSoldOut);

	function formatCountdown(ms: number): string {
		if (ms <= 0) return '마감됨';
		const hours = Math.floor(ms / 3600000);
		const mins = Math.floor((ms % 3600000) / 60000);
		const secs = Math.floor((ms % 60000) / 1000);
		if (hours > 24) {
			const days = Math.floor(hours / 24);
			return `${days}일 ${hours % 24}시간`;
		}
		return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
	}

	function formatPrice(n: number): string {
		return n.toLocaleString('ko-KR');
	}

	const statusConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' | 'ghost' }> = {
		open: { label: '진행 중', variant: 'default' },
		closed: { label: '마감', variant: 'secondary' },
		pickup_ready: { label: '수령 가능', variant: 'outline' },
		completed: { label: '완료', variant: 'secondary' },
		cancelled: { label: '취소됨', variant: 'destructive' }
	};

	let currentStatus = $derived(statusConfig[group.status] ?? { label: group.status, variant: 'secondary' as const });
</script>

<svelte:head>
	<title>{group.product_name} - {formatPrice(group.price)}원 | 모아오더</title>
	<meta property="og:title" content="{group.product_name} - {formatPrice(group.price)}원" />
	<meta property="og:description" content="{group.store_name}의 공구" />
	{#if group.image_url}
		<meta property="og:image" content={group.image_url} />
	{/if}
</svelte:head>

<main class="min-h-screen bg-background">
	<!-- Hero image -->
	{#if group.image_url}
		<div class="relative aspect-square w-full overflow-hidden">
			<img src={group.image_url} alt={group.product_name} class="h-full w-full object-cover" />
		</div>
	{:else}
		<div class="flex w-full aspect-video items-center justify-center bg-muted text-5xl">
			📦
		</div>
	{/if}

	<!-- Content -->
	<div class="px-5 pt-5 pb-32 space-y-5">
		<!-- Header -->
		<div class="space-y-2">
			<div class="flex items-center gap-2">
				<Badge variant={currentStatus.variant}>{currentStatus.label}</Badge>
				<span class="text-xs text-muted-foreground">{group.store_name}</span>
			</div>
			<h1 class="text-xl font-bold text-foreground leading-snug">{group.product_name}</h1>
			<p class="text-2xl font-black text-primary">{formatPrice(group.price)}원</p>
		</div>

		<!-- Countdown -->
		{#if group.status === 'open' && !isExpired}
			<div class="rounded-xl bg-primary/5 border border-primary/20 px-4 py-4 text-center">
				<p class="text-xs text-muted-foreground mb-1.5">마감까지</p>
				<p class="text-2xl font-black text-primary tabular-nums tracking-tight">{formatCountdown(remainingMs)}</p>
			</div>
		{/if}

		<!-- Group buy progress -->
		{#if group.type === 'group_buy' && group.min_quantity}
			{@const currentOrders = group.max_quantity ? (group.max_quantity - (group.remaining_qty ?? 0)) : 0}
			{@const pct = Math.min(100, (currentOrders / group.min_quantity) * 100)}
			<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-2.5">
				<div class="flex items-center justify-between text-sm">
					<span class="text-muted-foreground font-medium">공동구매 현황</span>
					<span class="font-semibold {currentOrders >= group.min_quantity ? 'text-green-600' : 'text-foreground'}">
						{currentOrders} / {group.min_quantity}개
					</span>
				</div>
				<div class="relative h-2.5 rounded-full bg-muted overflow-hidden">
					<div
						class="absolute inset-y-0 left-0 rounded-full transition-all duration-500 {pct >= 100 ? 'bg-green-500' : 'bg-primary'}"
						style="width: {pct}%"
					></div>
				</div>
				{#if currentOrders >= group.min_quantity}
					<p class="text-xs text-green-600 font-medium">최소 수량 달성! 공구가 확정됩니다</p>
				{:else}
					<p class="text-xs text-muted-foreground">{group.min_quantity - currentOrders}개 더 모이면 공구 확정</p>
				{/if}
			</div>
		{/if}

		<!-- Remaining quantity -->
		{#if group.remaining_qty !== null && group.remaining_qty !== undefined}
			<div class="flex items-center gap-2">
				{#if group.remaining_qty > 0}
					<span class="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700">
						잔여 {group.remaining_qty}개
					</span>
				{:else}
					<span class="inline-flex items-center rounded-full bg-destructive/10 px-3 py-1 text-xs font-medium text-destructive">
						품절
					</span>
				{/if}
			</div>
		{/if}

		<!-- Description -->
		{#if group.description}
			<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4">
				<p class="text-sm text-foreground whitespace-pre-wrap leading-relaxed">{group.description}</p>
			</div>
		{/if}

		<!-- Pickup slots -->
		{#if group.pickup_slots && group.pickup_slots.length > 0}
			<div class="space-y-2">
				<p class="text-sm font-semibold text-foreground">픽업 시간대</p>
				{#each group.pickup_slots as slot}
					<div class="rounded-xl bg-card ring-1 ring-border px-4 py-3">
						<p class="text-sm font-medium text-foreground">{slot.label}</p>
						<p class="text-xs text-muted-foreground mt-0.5">
							{new Date(slot.start_at).toLocaleString('ko-KR')} ~ {new Date(slot.end_at).toLocaleString('ko-KR')}
						</p>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Closed state info -->
		{#if group.status !== 'open' || isExpired}
			<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-3">
				{#if group.status === 'cancelled'}
					<div class="flex items-start gap-3">
						<span class="text-2xl shrink-0">😢</span>
						<div>
							<p class="text-sm font-semibold text-foreground">최소 수량 미달로 취소된 공구예요</p>
							<p class="text-xs text-muted-foreground mt-0.5">결제하셨다면 자동 환불됩니다</p>
						</div>
					</div>
				{:else if group.status === 'completed'}
					<div class="flex items-start gap-3">
						<span class="text-2xl shrink-0">✅</span>
						<div>
							<p class="text-sm font-semibold text-foreground">종료된 공구예요</p>
							<p class="text-xs text-muted-foreground mt-0.5">이 공구는 성공적으로 완료되었습니다</p>
						</div>
					</div>
				{:else if group.status === 'pickup_ready'}
					<div class="flex items-start gap-3">
						<span class="text-2xl shrink-0">🎁</span>
						<div>
							<p class="text-sm font-semibold text-foreground">수령 가능 상태예요</p>
							<p class="text-xs text-muted-foreground mt-0.5">매장에서 주문하신 상품을 수령해 주세요</p>
						</div>
					</div>
				{:else}
					<div class="flex items-start gap-3">
						<span class="text-2xl shrink-0">🔒</span>
						<div>
							<p class="text-sm font-semibold text-foreground">마감된 공구예요</p>
							<p class="text-xs text-muted-foreground mt-0.5">주문이 마감되었습니다</p>
						</div>
					</div>
				{/if}
				<a
					href="/g?store={group.store_id}"
					class="flex w-full items-center justify-center rounded-lg border border-primary/30 px-4 py-2.5 text-sm font-medium text-primary hover:bg-primary/5 transition-colors"
				>
					이 매장의 진행 중 공구 보기
				</a>
			</div>
		{/if}
	</div>

	<!-- Sticky bottom CTA -->
	<div class="fixed bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur-sm px-5 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
		{#if canOrder}
			<Button class="w-full" size="lg" onclick={() => goto(`/g/${group.public_id}/order`)}>
				주문하기
			</Button>
		{:else if isSoldOut && group.status === 'open'}
			<Button class="w-full" size="lg" disabled>품절</Button>
		{:else if group.status === 'cancelled'}
			<Button class="w-full" size="lg" variant="secondary" disabled>취소된 공구</Button>
		{:else if group.status === 'pickup_ready'}
			<Button class="w-full" size="lg" variant="secondary" disabled>수령 진행 중</Button>
		{:else if group.status === 'completed'}
			<Button class="w-full" size="lg" variant="secondary" disabled>종료됨</Button>
		{:else}
			<Button class="w-full" size="lg" variant="secondary" disabled>마감됨</Button>
		{/if}
	</div>
</main>
