<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Button } from '$lib/components/ui/button';
	import { api, ApiRequestError } from '$lib/api';
	import { requestPayment } from '$lib/payment';

	let { data } = $props();
	let group = $derived(data.group);
	let portoneStoreId = $derived(data.portoneStoreId);
	let portoneChannelKey = $derived(data.portoneChannelKey);

	let quantity = $state(1);
	let selectedSlotId = $state<string | null>(null);
	let error = $state('');
	let loading = $state(false);

	let maxQty = $derived(
		group.remaining_qty !== null ? Math.min(group.remaining_qty, 20) : 20
	);
	let totalAmount = $derived(group.price * quantity);

	function formatPrice(n: number) {
		return n.toLocaleString('ko-KR');
	}

	async function handleOrder() {
		error = '';
		if (group.type === 'pickup' && group.pickup_slots?.length > 0 && !selectedSlotId) {
			error = '픽업 시간대를 선택해주세요.';
			return;
		}
		loading = true;
		try {
			const prepare = await api.post<{
				hold_id: string;
				payment_id: string;
				store_id: string;
				amount: number;
				order_name: string;
			}>('/checkout/prepare', {
				group_id: group.group_id,
				quantity,
				pickup_slot_id: selectedSlotId ?? undefined
			});

			const result = await requestPayment({
				storeId: portoneStoreId,
				channelKey: portoneChannelKey,
				paymentId: prepare.payment_id,
				orderName: prepare.order_name,
				totalAmount: prepare.amount
			});

			if (!result.success) {
				error = result.errorMessage ?? '결제가 취소되었습니다.';
				return;
			}

			goto(`/g/${$page.params.publicId}/order/complete?paymentId=${prepare.payment_id}`);
		} catch (e) {
			error = e instanceof ApiRequestError ? e.message : '오류가 발생했습니다. 다시 시도해주세요.';
		} finally {
			loading = false;
		}
	}
</script>

<main class="min-h-screen bg-background pb-28">
	<!-- Header -->
	<div class="sticky top-0 z-10 flex items-center h-14 px-4 border-b border-border bg-background/95 backdrop-blur-sm">
		<button aria-label="뒤로 가기" onclick={() => history.back()} class="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted transition-colors -ml-2">
			<svg class="size-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
			</svg>
		</button>
		<h1 class="ml-2 text-base font-semibold text-foreground">주문하기</h1>
	</div>

	<div class="px-5 py-5 space-y-4">
		<!-- Product info -->
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4">
			<p class="text-xs text-muted-foreground">{group.store_name}</p>
			<p class="text-base font-bold text-foreground mt-0.5">{group.product_name}</p>
			<p class="text-lg font-black text-primary mt-1">{formatPrice(group.price)}원</p>
		</div>

		<!-- Quantity selector -->
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-3">
			<p class="text-sm font-semibold text-foreground">수량 선택</p>
			<div class="flex items-center gap-4">
				<button
					class="flex h-10 w-10 items-center justify-center rounded-full border-2 border-border text-lg font-bold text-foreground hover:border-primary hover:text-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
					onclick={() => (quantity = Math.max(1, quantity - 1))}
					disabled={quantity <= 1}
				>
					−
				</button>
				<span class="w-10 text-center text-2xl font-bold tabular-nums">{quantity}</span>
				<button
					class="flex h-10 w-10 items-center justify-center rounded-full border-2 border-border text-lg font-bold text-foreground hover:border-primary hover:text-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
					onclick={() => (quantity = Math.min(maxQty, quantity + 1))}
					disabled={quantity >= maxQty}
				>
					+
				</button>
				{#if group.remaining_qty !== null}
					<span class="text-xs text-muted-foreground">최대 {maxQty}개</span>
				{/if}
			</div>
		</div>

		<!-- Pickup slot selector -->
		{#if group.type === 'pickup' && group.pickup_slots?.length > 0}
			<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-3">
				<p class="text-sm font-semibold text-foreground">픽업 시간대 선택</p>
				<div class="space-y-2">
					{#each group.pickup_slots as slot}
						<label class="flex items-center gap-3 cursor-pointer rounded-lg border border-border px-3 py-2.5 hover:border-primary/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5">
							<input
								type="radio"
								name="pickup_slot"
								value={slot.id}
								bind:group={selectedSlotId}
								class="accent-primary"
							/>
							<span class="text-sm text-foreground">
								{slot.label}
								<span class="text-xs text-muted-foreground ml-1">
									{new Date(slot.start_at).toLocaleString('ko-KR', {
										month: 'short',
										day: 'numeric',
										hour: '2-digit',
										minute: '2-digit'
									})}
								</span>
							</span>
						</label>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Amount summary -->
		<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-2">
			<div class="flex justify-between text-sm">
				<span class="text-muted-foreground">단가</span>
				<span class="text-foreground">{formatPrice(group.price)}원</span>
			</div>
			<div class="flex justify-between text-sm">
				<span class="text-muted-foreground">수량</span>
				<span class="text-foreground">{quantity}개</span>
			</div>
			<div class="border-t border-border pt-2.5 mt-2 flex justify-between">
				<span class="text-sm font-semibold text-foreground">결제 금액</span>
				<span class="text-lg font-black text-primary">{formatPrice(totalAmount)}원</span>
			</div>
		</div>

		{#if error}
			<div class="rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
				{error}
			</div>
		{/if}
	</div>
</main>

<!-- Fixed bottom CTA -->
<div class="fixed bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur-sm px-5 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
	<Button class="w-full" size="lg" onclick={handleOrder} disabled={loading}>
		{loading ? '처리 중...' : `${formatPrice(totalAmount)}원 결제하기`}
	</Button>
</div>
