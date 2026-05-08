<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	type Group = {
		id: string;
		status: string;
		type: string;
		product_name: string;
		price: number;
		description?: string;
		image_url?: string;
		max_quantity?: number;
		min_quantity?: number;
		closes_at: string;
		pickup_slots: { id: string; label: string; start_at: string; end_at: string }[];
	};

	let group = $state<Group | null>(null);
	let productName = $state('');
	let price = $state('');
	let closesAt = $state('');
	let description = $state('');
	let maxQuantity = $state('');
	let minQuantity = $state('');
	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');

	const groupId = $derived($page.params.groupId);

	function toLocalDatetime(iso: string): string {
		const d = new Date(iso);
		const pad = (n: number) => n.toString().padStart(2, '0');
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

	onMount(async () => {
		try {
			const resp = await api.get<{ items: Group[] }>('/groups/my');
			group = resp.items.find((g) => g.id === groupId) ?? null;
			if (group) {
				productName = group.product_name;
				price = String(group.price);
				closesAt = toLocalDatetime(group.closes_at);
				description = group.description ?? '';
				maxQuantity = group.max_quantity ? String(group.max_quantity) : '';
				minQuantity = group.min_quantity ? String(group.min_quantity) : '';
			}
		} catch {
			error = '공구 정보를 불러올 수 없습니다';
		} finally {
			loading = false;
		}
	});

	async function handleSubmit() {
		error = '';
		saving = true;
		try {
			const body: Record<string, unknown> = {};
			if (productName.trim() !== group?.product_name) body.product_name = productName.trim();
			if (Number(price) !== group?.price) body.price = Number(price);
			if (new Date(closesAt).toISOString() !== group?.closes_at) body.closes_at = new Date(closesAt).toISOString();
			if (description.trim() !== (group?.description ?? '')) body.description = description.trim();
			if (maxQuantity && Number(maxQuantity) !== group?.max_quantity) body.max_quantity = Number(maxQuantity);
			if (minQuantity && Number(minQuantity) !== group?.min_quantity) body.min_quantity = Number(minQuantity);
			await api.patch(`/groups/${groupId}`, body);
			toast.success('공구가 수정되었습니다');
			goto(`/owner/groups/${groupId}`);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : '수정에 실패했습니다';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head>
	<title>공구 수정 - 모아오더</title>
</svelte:head>

<div class="mx-auto max-w-lg space-y-6 px-5 pt-6 pb-10">
	{#if loading}
		<div class="space-y-3">
			<div class="h-8 w-32 animate-pulse rounded-lg bg-muted"></div>
			{#each [0, 1, 2, 3] as _}
				<div class="h-14 animate-pulse rounded-2xl bg-muted"></div>
			{/each}
		</div>
	{:else if !group}
		<div class="flex flex-col items-center gap-4 rounded-2xl bg-muted/30 px-6 py-14 text-center">
			<div class="text-4xl">⚠️</div>
			<p class="text-[15px] font-bold text-foreground">공구를 찾을 수 없어요</p>
		</div>
	{:else}
		<h1 class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[32px]">
			공구 수정
		</h1>

		{#if error}
			<div class="rounded-xl bg-destructive/10 px-4 py-3 text-[13px] font-semibold text-destructive ring-1 ring-destructive/20">
				{error}
			</div>
		{/if}

		<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-5">
			<div class="space-y-2">
				<Label for="edit-name" class="text-[13px] font-bold text-foreground">상품명</Label>
				<Input id="edit-name" bind:value={productName} required />
			</div>
			<div class="space-y-2">
				<Label for="edit-price" class="text-[13px] font-bold text-foreground">가격 (원)</Label>
				<Input id="edit-price" type="number" bind:value={price} min="1" required />
			</div>
			<div class="space-y-2">
				<Label for="edit-closes" class="text-[13px] font-bold text-foreground">마감 시간</Label>
				<input
					id="edit-closes"
					type="datetime-local"
					class="flex h-12 w-full rounded-xl border border-input bg-background px-4 text-[14px] outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
					bind:value={closesAt}
					required
				/>
			</div>
			<div class="space-y-2">
				<Label for="edit-desc" class="text-[13px] font-bold text-foreground">상품 설명</Label>
				<textarea
					id="edit-desc"
					class="w-full resize-none rounded-xl border border-input bg-background px-4 py-3 text-[14px] outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20"
					rows="3"
					bind:value={description}
				></textarea>
			</div>
			{#if group.type === 'group_buy'}
				<div class="space-y-2">
					<Label for="edit-min" class="text-[13px] font-bold text-foreground">최소 수량</Label>
					<Input id="edit-min" type="number" bind:value={minQuantity} min="1" />
				</div>
			{/if}
			<div class="space-y-2">
				<Label for="edit-max" class="text-[13px] font-bold text-foreground">판매 가능 수량</Label>
				<Input id="edit-max" type="number" bind:value={maxQuantity} min="1" />
			</div>

			<div class="flex gap-3 pt-1">
				<Button type="button" variant="outline" class="flex-1" onclick={() => goto(`/owner/groups/${groupId}`)}>취소</Button>
				<Button type="submit" class="flex-1" disabled={saving}>
					{saving ? '저장 중...' : '저장'}
				</Button>
			</div>
		</form>
	{/if}
</div>
