<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { fetchMe } from '$lib/stores/auth';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	let storeName = $state('');
	let ownerName = $state('');
	let contact = $state('');
	let region = $state('');
	let category = $state('');
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!storeName || !ownerName || !contact || !region || !category) {
			error = '모든 항목을 입력해주세요';
			return;
		}
		loading = true;
		error = '';
		try {
			await api.post('/onboarding/owner', {
				store_name: storeName,
				owner_name: ownerName,
				contact,
				region,
				category
			});
			await fetchMe();
			goto('/owner');
		} catch {
			error = '등록에 실패했습니다. 다시 시도해주세요.';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>매장 등록 - 모아오더</title>
</svelte:head>

<main class="flex min-h-screen flex-col items-center justify-start bg-gradient-to-b from-gray-50 to-gray-100 px-5 py-12">
	<div class="w-full max-w-sm space-y-8">
		<!-- Header -->
		<div class="space-y-1.5">
			<h1 class="text-2xl font-bold text-foreground">매장 등록</h1>
			<p class="text-sm text-muted-foreground">공동구매를 시작하려면 매장 정보를 입력해주세요</p>
		</div>

		<!-- Form -->
		<form class="space-y-5" onsubmit={handleSubmit}>
			<div class="space-y-1.5">
				<Label for="store-name">매장명 <span class="text-primary">*</span></Label>
				<Input id="store-name" placeholder="예: 행복한 베이커리" bind:value={storeName} required />
			</div>
			<div class="space-y-1.5">
				<Label for="owner-name">운영자명 <span class="text-primary">*</span></Label>
				<Input id="owner-name" placeholder="이름" bind:value={ownerName} required />
			</div>
			<div class="space-y-1.5">
				<Label for="contact">연락처 <span class="text-primary">*</span></Label>
				<Input id="contact" placeholder="010-0000-0000" bind:value={contact} required />
			</div>
			<div class="space-y-1.5">
				<Label for="region">지역 <span class="text-primary">*</span></Label>
				<Input id="region" placeholder="예: 서울 강남구" bind:value={region} required />
			</div>
			<div class="space-y-1.5">
				<Label for="category">카테고리 <span class="text-primary">*</span></Label>
				<Input id="category" placeholder="예: 베이커리, 농산물" bind:value={category} required />
			</div>

			{#if error}
				<div class="rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
					{error}
				</div>
			{/if}

			<Button type="submit" class="w-full" size="lg" disabled={loading}>
				{loading ? '처리 중...' : '매장 등록하기'}
			</Button>
		</form>
	</div>
</main>
