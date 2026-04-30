<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { fetchMe } from '$lib/stores/auth';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	let nickname = $state('');
	let region = $state('');
	let category = $state('');
	let loading = $state(false);
	let error = $state('');

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!nickname.trim()) {
			error = '닉네임을 입력해주세요';
			return;
		}
		loading = true;
		error = '';
		try {
			await api.post('/onboarding/customer', {
				nickname: nickname.trim(),
				region: region || null,
				category: category || null
			});
			await fetchMe();
			goto('/');
		} catch {
			error = '등록에 실패했습니다. 다시 시도해주세요.';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>프로필 설정 - 모아오더</title>
</svelte:head>

<main class="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-gray-50 to-gray-100 px-5 py-12">
	<div class="w-full max-w-sm space-y-8">
		<!-- Header -->
		<div class="space-y-1.5">
			<h1 class="text-2xl font-bold text-foreground">프로필 설정</h1>
			<p class="text-sm text-muted-foreground">닉네임을 설정하고 시작해보세요</p>
		</div>

		<!-- Form -->
		<form class="space-y-5" onsubmit={handleSubmit}>
			<div class="space-y-1.5">
				<Label for="nickname">닉네임 <span class="text-primary">*</span></Label>
				<Input id="nickname" placeholder="닉네임을 입력하세요" bind:value={nickname} required />
			</div>
			<div class="space-y-1.5">
				<Label for="region">지역 <span class="text-muted-foreground text-xs">(선택)</span></Label>
				<Input id="region" placeholder="예: 서울 강남구" bind:value={region} />
			</div>
			<div class="space-y-1.5">
				<Label for="category">관심 카테고리 <span class="text-muted-foreground text-xs">(선택)</span></Label>
				<Input id="category" placeholder="예: 베이커리, 농산물" bind:value={category} />
			</div>

			{#if error}
				<div class="rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
					{error}
				</div>
			{/if}

			<Button type="submit" class="w-full" size="lg" disabled={loading}>
				{loading ? '처리 중...' : '시작하기'}
			</Button>
		</form>

		<div class="text-center">
			<button
				class="text-sm text-muted-foreground hover:text-primary transition-colors underline-offset-2 hover:underline"
				onclick={() => goto('/onboarding/owner')}
			>
				사장님이신가요? 매장 등록하기
			</button>
		</div>
	</div>
</main>
