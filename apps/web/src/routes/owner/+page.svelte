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

<div class="px-5 pt-6 pb-8 space-y-6 max-w-3xl">
	<!-- Page header -->
	<div class="space-y-1">
		<h1 class="text-[24px] font-black tracking-[-0.03em] text-foreground sm:text-[28px]">대시보드</h1>
		<p class="text-sm text-muted-foreground">{$user?.nickname ?? '사장'}님의 매장 현황</p>
	</div>

	{#if loading}
		<!-- Skeleton stats -->
		<div class="grid grid-cols-2 md:grid-cols-3 gap-3">
			{#each [0, 1, 2] as _}
				<div class="rounded-xl bg-muted animate-pulse h-20"></div>
			{/each}
		</div>
		<div class="space-y-2.5">
			{#each [0, 1] as _}
				<div class="rounded-xl bg-muted animate-pulse h-16"></div>
			{/each}
		</div>
	{:else if error}
		<div class="flex flex-col items-center gap-3 py-12 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-sm text-muted-foreground">{error}</p>
			<button
				class="text-sm text-primary underline underline-offset-2"
				onclick={fetchDashboard}
			>
				다시 시도
			</button>
		</div>
	{:else if summary}
		<!-- Stats grid -->
		<div class="grid grid-cols-2 md:grid-cols-3 gap-3">
			<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 text-center">
				<p class="text-3xl font-black text-primary">{summary.active_group_count}</p>
				<p class="text-xs text-muted-foreground mt-1">진행 중 공구</p>
			</div>
			<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 text-center">
				<p class="text-3xl font-black text-foreground">{summary.total_order_count}</p>
				<p class="text-xs text-muted-foreground mt-1">총 주문</p>
			</div>
			<div class="col-span-2 md:col-span-1 rounded-xl bg-card ring-1 ring-border px-4 py-4 text-center">
				<p class="text-2xl font-black text-green-600">
					₩{summary.estimated_revenue.toLocaleString()}
				</p>
				<p class="text-xs text-muted-foreground mt-1">예상 매출</p>
			</div>
		</div>

		<!-- Alert banners -->
		{#if alerts && (alerts.picking_ready_groups.length > 0 || alerts.cancel_request_count > 0)}
			<section class="space-y-2.5">
				<h2 class="text-[17px] font-bold tracking-[-0.02em] text-foreground sm:text-[20px]">조치 필요</h2>
				{#if alerts.picking_ready_groups.length > 0}
					<a
						href="/owner/groups"
						class="flex items-center justify-between rounded-xl bg-amber-50 border border-amber-200 px-4 py-3.5 hover:bg-amber-100 transition-colors active:scale-[0.99]"
					>
						<div>
							<p class="text-sm font-semibold text-amber-800">피킹 리스트 확인</p>
							<p class="text-xs text-amber-600 mt-0.5">
								{alerts.picking_ready_groups.length}개 공구 준비 필요
							</p>
						</div>
						<svg class="size-4 text-amber-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				{/if}
				{#if alerts.cancel_request_count > 0}
					<a
						href="/owner/groups"
						class="flex items-center justify-between rounded-xl bg-destructive/5 border border-destructive/20 px-4 py-3.5 hover:bg-destructive/10 transition-colors active:scale-[0.99]"
					>
						<div>
							<p class="text-sm font-semibold text-destructive">취소 요청 {alerts.cancel_request_count}건</p>
							<p class="text-xs text-destructive/70 mt-0.5">승인 또는 거절이 필요합니다</p>
						</div>
						<svg class="size-4 text-destructive/60 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				{/if}
			</section>
		{/if}

		<!-- Active groups -->
		<section class="space-y-3">
			<div class="flex items-center justify-between">
				<h2 class="text-[17px] font-bold tracking-[-0.02em] text-foreground sm:text-[20px]">진행 중 공구</h2>
				<a href="/owner/groups" class="text-xs text-primary hover:underline underline-offset-2">전체 보기</a>
			</div>

			{#if summary.groups.length === 0}
				<div class="flex flex-col items-center gap-4 rounded-xl border border-dashed border-border bg-card py-12 text-center">
					<div class="text-3xl">📦</div>
					<div class="space-y-1">
						<p class="text-sm font-semibold text-foreground">진행 중인 공구가 없습니다</p>
						<p class="text-xs text-muted-foreground">새 공구를 만들어 수익을 시작해보세요</p>
					</div>
					<a
						href="/owner/groups/create"
						class="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
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
								class="block rounded-xl bg-card ring-1 ring-border px-4 py-4 hover:ring-primary/30 transition-all active:scale-[0.99] space-y-2"
							>
								<div class="flex items-start justify-between gap-2">
									<p class="text-sm font-semibold text-foreground leading-snug">{group.product_name}</p>
									<span class="shrink-0 text-xs font-medium text-primary/80 bg-primary/10 rounded-full px-2.5 py-0.5">
										{timeUntil(group.closes_at)} 남음
									</span>
								</div>
								<div class="flex gap-4 text-xs text-muted-foreground">
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
