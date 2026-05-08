<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { api } from '$lib/api';
	import { user } from '$lib/stores/auth';

	interface GroupSummaryItem {
		id: string;
		product_name: string;
		closes_at: string;
		order_count: number;
		remaining_qty: number | null;
	}

	interface DashboardSummary {
		active_group_count: number;
		total_order_count: number;
		estimated_revenue: number;
		groups: GroupSummaryItem[];
	}

	interface PickingAlertItem {
		id: string;
		product_name: string;
		order_count: number;
	}

	interface DashboardAlert {
		picking_ready_groups: PickingAlertItem[];
		cancel_request_count: number;
	}

	let summary: DashboardSummary | null = $state(null);
	let alerts: DashboardAlert | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let pollInterval: ReturnType<typeof setInterval>;

	async function fetchDashboard() {
		try {
			[summary, alerts] = await Promise.all([
				api.get<DashboardSummary>('/dashboard/summary'),
				api.get<DashboardAlert>('/dashboard/alerts')
			]);
			error = '';
		} catch {
			error = '데이터를 불러오지 못했습니다';
		} finally {
			loading = false;
		}
	}

	function timeUntil(closesAt: string): string {
		const diff = new Date(closesAt).getTime() - Date.now();
		if (diff <= 0) return '마감됨';
		const hours = Math.floor(diff / 3_600_000);
		const mins = Math.floor((diff % 3_600_000) / 60_000);
		if (hours > 0) return `${hours}시간 ${mins}분`;
		return `${mins}분`;
	}

	onMount(() => {
		fetchDashboard();
		pollInterval = setInterval(fetchDashboard, 10_000);
	});

	onDestroy(() => clearInterval(pollInterval));
</script>

<svelte:head>
	<title>대시보드 - 모아오더</title>
</svelte:head>

<div class="mx-auto max-w-3xl space-y-6 px-5 pt-6 pb-8">
	<!-- Page header -->
	<div class="space-y-1.5">
		<h1 class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[32px]">
			대시보드
		</h1>
		<p class="text-[14px] text-muted-foreground">{$user?.nickname ?? '사장'}님의 매장 현황</p>
	</div>

	{#if loading}
		<!-- Skeleton stats -->
		<div class="grid grid-cols-2 gap-3 md:grid-cols-3">
			{#each [0, 1, 2] as _}
				<div class="h-24 animate-pulse rounded-2xl bg-muted"></div>
			{/each}
		</div>
		<div class="space-y-2.5">
			{#each [0, 1] as _}
				<div class="h-16 animate-pulse rounded-2xl bg-muted"></div>
			{/each}
		</div>
	{:else if error}
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-[14px] text-muted-foreground">{error}</p>
			<button
				class="text-[13px] font-semibold text-primary underline-offset-2 hover:underline"
				onclick={fetchDashboard}
			>
				다시 시도
			</button>
		</div>
	{:else if summary}
		<!-- Stats grid -->
		<div class="grid grid-cols-2 gap-3 md:grid-cols-3">
			<div class="rounded-2xl bg-card px-5 py-5 text-center ring-1 ring-border">
				<p class="text-[28px] font-bold tracking-[-0.03em] text-primary">{summary.active_group_count}</p>
				<p class="mt-1 text-[12px] font-semibold text-muted-foreground">진행 중 공구</p>
			</div>
			<div class="rounded-2xl bg-card px-5 py-5 text-center ring-1 ring-border">
				<p class="text-[28px] font-bold tracking-[-0.03em] text-foreground">{summary.total_order_count}</p>
				<p class="mt-1 text-[12px] font-semibold text-muted-foreground">총 주문</p>
			</div>
			<div class="col-span-2 rounded-2xl bg-card px-5 py-5 text-center ring-1 ring-border md:col-span-1">
				<p class="text-[24px] font-bold tracking-[-0.03em] text-emerald-600">
					{summary.estimated_revenue.toLocaleString()}원
				</p>
				<p class="mt-1 text-[12px] font-semibold text-muted-foreground">예상 매출</p>
			</div>
		</div>

		<!-- Alert banners -->
		{#if alerts && (alerts.picking_ready_groups.length > 0 || alerts.cancel_request_count > 0)}
			<section class="space-y-2.5">
				<h2 class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">조치 필요</h2>
				{#if alerts.picking_ready_groups.length > 0}
					<a
						href="/owner/groups"
						class="flex items-center justify-between rounded-2xl bg-amber-50 px-5 py-4 ring-1 ring-amber-100 transition-colors hover:bg-amber-100/60 active:scale-[0.99]"
					>
						<div class="space-y-1">
							<p class="text-[14px] font-bold text-amber-800">피킹 리스트 확인</p>
							<p class="text-[12px] text-amber-700/80">
								{alerts.picking_ready_groups.length}개 공구 준비 필요
							</p>
						</div>
						<svg class="size-4 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				{/if}
				{#if alerts.cancel_request_count > 0}
					<a
						href="/owner/groups"
						class="flex items-center justify-between rounded-2xl bg-destructive/5 px-5 py-4 ring-1 ring-destructive/20 transition-colors hover:bg-destructive/10 active:scale-[0.99]"
					>
						<div class="space-y-1">
							<p class="text-[14px] font-bold text-destructive">취소 요청 {alerts.cancel_request_count}건</p>
							<p class="text-[12px] text-destructive/70">승인 또는 거절이 필요해요</p>
						</div>
						<svg class="size-4 shrink-0 text-destructive/60" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				{/if}
			</section>
		{/if}

		<!-- Active groups -->
		<section class="space-y-3">
			<div class="flex items-end justify-between">
				<h2 class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">진행 중 공구</h2>
				<a href="/owner/groups" class="text-[12px] font-semibold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">전체 보기</a>
			</div>

			{#if summary.groups.length === 0}
				<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
					<div class="text-4xl">📦</div>
					<div class="space-y-1.5">
						<p class="text-[15px] font-bold text-foreground">진행 중인 공구가 없어요</p>
						<p class="text-[13px] text-muted-foreground">새 공구를 만들어 수익을 시작해보세요</p>
					</div>
					<a
						href="/owner/groups/create"
						class="rounded-xl bg-primary px-5 py-2.5 text-[13px] font-bold text-primary-foreground transition-colors hover:bg-primary/90"
					>
						새 공구 만들기
					</a>
				</div>
			{:else}
				<ul class="space-y-2.5">
					{#each summary.groups as group}
						<li>
							<a
								href="/owner/groups/{group.id}"
								class="block space-y-2 rounded-2xl bg-card px-5 py-4 ring-1 ring-border transition-all hover:ring-primary/30 active:scale-[0.99]"
							>
								<div class="flex items-start justify-between gap-3">
									<p class="text-[14px] font-bold leading-snug text-foreground">{group.product_name}</p>
									<span class="shrink-0 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-bold text-primary">
										{timeUntil(group.closes_at)} 남음
									</span>
								</div>
								<div class="flex gap-4 text-[12px] text-muted-foreground">
									<span>주문 <strong class="text-foreground">{group.order_count}건</strong></span>
									{#if group.remaining_qty !== null}
										<span>잔여 <strong class="text-foreground">{group.remaining_qty}개</strong></span>
									{/if}
								</div>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}
</div>

<!-- FAB (mobile only) -->
<a
	href="/owner/groups/create"
	class="fixed bottom-6 right-4 md:hidden flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 hover:bg-primary/90 transition-colors active:scale-95"
	aria-label="새 공구 만들기"
>
	<svg class="size-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
		<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
	</svg>
</a>
