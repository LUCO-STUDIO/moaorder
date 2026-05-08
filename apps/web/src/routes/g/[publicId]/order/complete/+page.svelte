<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { Button } from '$lib/components/ui/button';
	import { api, ApiRequestError } from '$lib/api';

	let paymentId = $derived($page.url.searchParams.get('paymentId') ?? '');
	let publicId = $derived($page.params.publicId);

	type PollStatus = 'polling' | 'paid' | 'timeout' | 'error';

	let status = $state<PollStatus>('polling');
	let orderId = $state<string | null>(null);
	let errorMsg = $state('');

	const POLL_INTERVAL_MS = 2000;
	const POLL_TIMEOUT_MS = 30000;

	onMount(() => {
		if (!paymentId) {
			status = 'error';
			errorMsg = '결제 정보가 없습니다.';
			return;
		}
		const startTime = Date.now();
		let timerId: ReturnType<typeof setTimeout>;

		async function poll() {
			try {
				const res = await api.get<{ status: string; order_id?: string }>(
					`/orders/by-payment/${paymentId}`
				);
				if (res.status === 'paid' && res.order_id) {
					orderId = res.order_id;
					status = 'paid';
					return;
				}
				if (Date.now() - startTime >= POLL_TIMEOUT_MS) {
					status = 'timeout';
					return;
				}
				timerId = setTimeout(poll, POLL_INTERVAL_MS);
			} catch (e) {
				if (e instanceof ApiRequestError && e.status === 404) {
					if (Date.now() - startTime >= POLL_TIMEOUT_MS) {
						status = 'timeout';
					} else {
						timerId = setTimeout(poll, POLL_INTERVAL_MS);
					}
				} else {
					status = 'error';
					errorMsg = '오류가 발생했습니다.';
				}
			}
		}

		poll();
		return () => clearTimeout(timerId);
	});
</script>

<svelte:head>
	<title>주문 완료 - 모아오더</title>
</svelte:head>

<main class="flex min-h-screen flex-col items-center justify-center bg-background px-5 py-10">
	<div class="w-full max-w-sm">
		{#if status === 'polling'}
			<div class="space-y-5 rounded-3xl bg-card px-6 py-14 text-center ring-1 ring-border">
				<div class="flex justify-center">
					<div class="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
				</div>
				<div class="space-y-1.5">
					<p class="text-[18px] font-bold tracking-[-0.02em] text-foreground">주문 확인 중</p>
					<p class="text-[13px] text-muted-foreground">잠시만 기다려주세요</p>
				</div>
			</div>

		{:else if status === 'paid'}
			<div class="space-y-7 rounded-3xl bg-card px-6 py-14 text-center ring-1 ring-border">
				<div class="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-emerald-100 text-5xl">
					🎉
				</div>
				<div class="space-y-2">
					<p class="text-[22px] font-bold tracking-[-0.03em] text-foreground">주문이 완료됐어요</p>
					<p class="text-[14px] leading-relaxed text-muted-foreground">
						자동으로 매장을 구독했어요.<br />공구 소식을 알림으로 받아보세요.
					</p>
				</div>
				<div class="space-y-2.5">
					<Button class="w-full" size="lg" href="/orders">주문 내역 보기</Button>
					<Button variant="outline" class="w-full" href="/g/{publicId}">공구 페이지로 돌아가기</Button>
				</div>
			</div>

		{:else if status === 'timeout'}
			<div class="space-y-7 rounded-3xl bg-card px-6 py-14 text-center ring-1 ring-border">
				<div class="text-5xl">⏱️</div>
				<div class="space-y-2">
					<p class="text-[20px] font-bold tracking-[-0.02em] text-foreground">주문 확인이 지연되고 있어요</p>
					<p class="text-[14px] leading-relaxed text-muted-foreground">
						결제는 정상 처리되었을 수 있어요.<br />주문 내역에서 확인해주세요.
					</p>
				</div>
				<Button class="w-full" size="lg" href="/orders">주문 내역 확인하기</Button>
			</div>

		{:else}
			<div class="space-y-7 rounded-3xl bg-card px-6 py-14 text-center ring-1 ring-border">
				<div class="text-5xl">⚠️</div>
				<div class="space-y-2">
					<p class="text-[20px] font-bold tracking-[-0.02em] text-foreground">오류가 발생했어요</p>
					<p class="text-[14px] text-muted-foreground">{errorMsg}</p>
				</div>
				<Button class="w-full" href="/g/{publicId}">공구 페이지로 돌아가기</Button>
			</div>
		{/if}
	</div>
</main>
