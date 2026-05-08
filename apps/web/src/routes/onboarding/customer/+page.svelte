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

<main class="flex min-h-screen flex-col bg-background px-5 py-12">
	<div class="mx-auto w-full max-w-sm space-y-8">
		<!-- Header -->
		<div class="space-y-2">
			<h1 class="text-[26px] font-bold leading-tight tracking-[-0.03em] text-foreground sm:text-[30px]">
				프로필 설정
			</h1>
			<p class="text-[14px] leading-relaxed text-muted-foreground">닉네임을 설정하고 시작해보세요</p>
		</div>

		<!-- Form -->
		<form class="space-y-5" onsubmit={handleSubmit}>
			<div class="space-y-2">
				<Label for="nickname" class="text-[13px] font-bold text-foreground">
					닉네임 <span class="text-primary">*</span>
				</Label>
				<Input id="nickname" placeholder="닉네임을 입력하세요" bind:value={nickname} required />
			</div>
			<div class="space-y-2">
				<Label for="region" class="text-[13px] font-bold text-foreground">
					지역 <span class="text-[11px] font-medium text-muted-foreground">(선택)</span>
				</Label>
				<Input id="region" placeholder="예: 서울 강남구" bind:value={region} />
			</div>
			<div class="space-y-2">
				<Label for="category" class="text-[13px] font-bold text-foreground">
					관심 카테고리 <span class="text-[11px] font-medium text-muted-foreground">(선택)</span>
				</Label>
				<Input id="category" placeholder="예: 베이커리, 농산물" bind:value={category} />
			</div>

			{#if error}
				<div class="rounded-xl bg-destructive/10 px-4 py-3 text-[13px] font-semibold text-destructive ring-1 ring-destructive/20">
					{error}
				</div>
			{/if}

			<Button type="submit" class="w-full" size="lg" disabled={loading}>
				{loading ? '처리 중...' : '시작하기'}
			</Button>
		</form>

		<div class="text-center">
			<button
				class="text-[13px] font-semibold text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline"
				onclick={() => goto('/onboarding/owner')}
			>
				사장님이신가요? 매장 등록하기
			</button>
		</div>
	</div>
</main>
