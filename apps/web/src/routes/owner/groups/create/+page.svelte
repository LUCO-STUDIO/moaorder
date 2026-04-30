<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	type GroupType = 'reservation' | 'group_buy' | 'pickup';
	type PickupSlot = { label: string; start_at: string; end_at: string };

	let productName = $state('');
	let price = $state('');
	let closesAt = $state('');
	let quickClose = $state<string>('');
	let type = $state<GroupType>('reservation');
	let description = $state('');
	let maxQuantity = $state('');
	let minQuantity = $state('');
	let imageUrl = $state('');
	let pickupSlots = $state<PickupSlot[]>([]);
	let showAdvanced = $state(false);
	let loading = $state(false);
	let uploading = $state(false);
	let error = $state('');
	let createdGroup = $state<{ public_id: string; product_name: string } | null>(null);

	function setQuickClose(option: string) {
		quickClose = option;
		const now = new Date();
		if (option === 'today_18') {
			const d = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 0, 0);
			if (d <= now) d.setDate(d.getDate() + 1);
			closesAt = toLocalISOString(d);
		} else if (option === 'today_24') {
			const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0);
			closesAt = toLocalISOString(d);
		} else {
			closesAt = '';
		}
	}

	function toLocalISOString(d: Date): string {
		const pad = (n: number) => n.toString().padStart(2, '0');
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

	function addPickupSlot() {
		pickupSlots = [...pickupSlots, { label: '', start_at: '', end_at: '' }];
	}

	function removePickupSlot(index: number) {
		pickupSlots = pickupSlots.filter((_, i) => i !== index);
	}

	async function handleImageUpload(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		uploading = true;
		try {
			const { upload_url, public_url } = await api.post<{ upload_url: string; public_url: string }>(
				'/uploads/presign',
				{ filename: file.name, content_type: file.type }
			);
			await fetch(upload_url, {
				method: 'PUT',
				body: file,
				headers: { 'Content-Type': file.type }
			});
			imageUrl = public_url;
			toast.success('이미지가 업로드되었습니다');
		} catch {
			toast.error('이미지 업로드에 실패했습니다');
		} finally {
			uploading = false;
		}
	}

	async function handleSubmit() {
		error = '';
		if (!productName.trim()) { error = '상품명을 입력해주세요'; return; }
		if (!price || Number(price) <= 0) { error = '가격을 입력해주세요'; return; }
		if (!closesAt) { error = '마감 시간을 선택해주세요'; return; }

		loading = true;
		try {
			const body: Record<string, unknown> = {
				product_name: productName.trim(),
				price: Number(price),
				closes_at: new Date(closesAt).toISOString(),
				type
			};
			if (description.trim()) body.description = description.trim();
			if (imageUrl) body.image_url = imageUrl;
			if (maxQuantity) body.max_quantity = Number(maxQuantity);
			if (type === 'group_buy' && minQuantity) body.min_quantity = Number(minQuantity);
			if (type === 'pickup' && pickupSlots.length > 0) {
				body.pickup_slots = pickupSlots
					.filter((s) => s.label && s.start_at && s.end_at)
					.map((s, i) => ({
						label: s.label,
						start_at: new Date(s.start_at).toISOString(),
						end_at: new Date(s.end_at).toISOString(),
						sort_order: i
					}));
			}
			const result = await api.post<{ public_id: string; product_name: string }>('/groups', body);
			createdGroup = result;
			toast.success('공구가 게시되었습니다!');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : '공구 생성에 실패했습니다';
		} finally {
			loading = false;
		}
	}

	function copyShareLink() {
		if (!createdGroup) return;
		const url = `${window.location.origin}/g/${createdGroup.public_id}`;
		navigator.clipboard.writeText(url);
		toast.success('링크가 복사되었습니다!');
	}

	function resetForm() {
		createdGroup = null;
		productName = '';
		price = '';
		closesAt = '';
		quickClose = '';
		description = '';
		imageUrl = '';
		maxQuantity = '';
		minQuantity = '';
		pickupSlots = [];
	}
</script>

<svelte:head>
	<title>새 공구 만들기 - 모아오더</title>
</svelte:head>

<div class="px-5 pt-6 pb-10 max-w-lg space-y-6">
	{#if createdGroup}
		<!-- Success state -->
		<div class="flex flex-col items-center text-center gap-6 py-10">
			<div class="flex h-20 w-20 items-center justify-center rounded-2xl bg-green-100 text-4xl">
				🎉
			</div>
			<div class="space-y-1">
				<h1 class="text-xl font-bold text-foreground">공구가 게시되었습니다!</h1>
				<p class="text-sm text-muted-foreground">{createdGroup.product_name}</p>
			</div>

			<div class="w-full rounded-xl bg-card ring-1 ring-border px-4 py-4 text-left space-y-3">
				<p class="text-xs font-medium text-muted-foreground">공유 링크</p>
				<p class="text-sm font-mono break-all text-primary">{window.location.origin}/g/{createdGroup.public_id}</p>
				<Button variant="outline" class="w-full" onclick={copyShareLink}>
					<svg class="size-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
					</svg>
					링크 복사
				</Button>
			</div>

			<div class="flex w-full gap-3">
				<Button variant="outline" class="flex-1" onclick={() => goto('/owner/groups')}>공구 목록</Button>
				<Button class="flex-1" onclick={resetForm}>새 공구 만들기</Button>
			</div>
		</div>
	{:else}
		<h1 class="text-2xl font-bold text-foreground">새 공구 만들기</h1>

		{#if error}
			<div class="rounded-xl bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
				{error}
			</div>
		{/if}

		<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-5">
			<!-- Product name -->
			<div class="space-y-1.5">
				<Label for="product-name">상품명 <span class="text-primary">*</span></Label>
				<Input id="product-name" bind:value={productName} placeholder="예: 수제 쿠키 세트" required />
			</div>

			<!-- Price -->
			<div class="space-y-1.5">
				<Label for="price">가격 (원) <span class="text-primary">*</span></Label>
				<Input id="price" type="number" bind:value={price} placeholder="5000" min="1" required />
			</div>

			<!-- Close time -->
			<div class="space-y-2">
				<Label>마감 시간 <span class="text-primary">*</span></Label>
				<div class="flex gap-2">
					{#each [{ key: 'today_18', label: '오늘 오후6시' }, { key: 'today_24', label: '오늘 자정' }, { key: 'custom', label: '직접 입력' }] as opt}
						<button
							type="button"
							class="flex-1 rounded-lg border py-2 text-sm font-medium transition-colors {quickClose === opt.key
								? 'border-primary bg-primary/5 text-primary'
								: 'border-border text-muted-foreground hover:text-foreground'}"
							onclick={() => setQuickClose(opt.key)}
						>
							{opt.label}
						</button>
					{/each}
				</div>
				{#if quickClose === 'custom' || (closesAt && quickClose !== 'today_18' && quickClose !== 'today_24')}
					<input
						type="datetime-local"
						class="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-colors"
						bind:value={closesAt}
					/>
				{/if}
				{#if closesAt && quickClose !== 'custom'}
					<p class="text-xs text-muted-foreground">
						마감: {new Date(closesAt).toLocaleString('ko-KR', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
					</p>
				{/if}
			</div>

			<!-- Image upload -->
			<div class="space-y-2">
				<Label>상품 사진</Label>
				<input
					type="file"
					accept="image/*"
					onchange={handleImageUpload}
					class="w-full text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-primary/10 file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary hover:file:bg-primary/20 transition"
				/>
				{#if uploading}
					<p class="text-xs text-muted-foreground flex items-center gap-1.5">
						<span class="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent"></span>
						업로드 중...
					</p>
				{/if}
				{#if imageUrl}
					<img src={imageUrl} alt="상품 이미지" class="h-28 w-28 rounded-xl object-cover" />
				{/if}
			</div>

			<!-- Advanced toggle -->
			<button
				type="button"
				class="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
				onclick={() => (showAdvanced = !showAdvanced)}
			>
				<svg class="size-4 transition-transform {showAdvanced ? 'rotate-180' : ''}" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
				</svg>
				{showAdvanced ? '고급 옵션 접기' : '고급 옵션 펼치기'}
			</button>

			{#if showAdvanced}
				<div class="rounded-xl bg-card ring-1 ring-border px-4 py-4 space-y-5">
					<!-- Group type -->
					<div class="space-y-1.5">
						<Label for="type">공구 타입</Label>
						<select
							id="type"
							class="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-colors"
							bind:value={type}
						>
							<option value="reservation">예약주문형</option>
							<option value="group_buy">공동구매형</option>
							<option value="pickup">픽업형</option>
						</select>
					</div>

					{#if type === 'group_buy'}
						<div class="space-y-1.5">
							<Label for="min-qty">최소 수량</Label>
							<Input id="min-qty" type="number" bind:value={minQuantity} placeholder="최소 주문 수" min="1" />
						</div>
					{/if}

					<div class="space-y-1.5">
						<Label for="max-qty">판매 가능 수량</Label>
						<Input id="max-qty" type="number" bind:value={maxQuantity} placeholder="미입력 시 무제한" min="1" />
					</div>

					<div class="space-y-1.5">
						<Label for="description">상품 설명</Label>
						<textarea
							id="description"
							class="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none resize-none transition-colors"
							rows="3"
							bind:value={description}
							placeholder="상품에 대한 추가 설명..."
						></textarea>
					</div>

					{#if type === 'pickup'}
						<div class="space-y-3">
							<Label>픽업 시간대</Label>
							{#each pickupSlots as slot, i}
								<div class="rounded-xl border border-border p-3.5 space-y-3">
									<div class="flex items-center justify-between">
										<span class="text-xs font-medium text-muted-foreground">슬롯 {i + 1}</span>
										<button type="button" class="text-xs text-destructive hover:underline" onclick={() => removePickupSlot(i)}>삭제</button>
									</div>
									<div class="space-y-1.5">
										<Label>라벨</Label>
										<Input bind:value={slot.label} placeholder="예: 오전 10-12시" />
									</div>
									<div class="space-y-1.5">
										<Label>시작</Label>
										<Input type="datetime-local" bind:value={slot.start_at} />
									</div>
									<div class="space-y-1.5">
										<Label>종료</Label>
										<Input type="datetime-local" bind:value={slot.end_at} />
									</div>
								</div>
							{/each}
							<button
								type="button"
								class="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border py-2.5 text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors"
								onclick={addPickupSlot}
							>
								<svg class="size-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
								</svg>
								시간대 추가
							</button>
						</div>
					{/if}
				</div>
			{/if}

			<Button type="submit" size="lg" class="w-full" disabled={loading}>
				{loading ? '처리 중...' : '공구 게시하기'}
			</Button>
		</form>
	{/if}
</div>
