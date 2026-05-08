<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';

	type Status = 'loading' | 'success' | 'error';
	let status = $state<Status>('loading');
	let errorMessage = $state('');

	onMount(async () => {
		const token = page.url.searchParams.get('token');
		if (!token) {
			status = 'error';
			errorMessage = '인증 링크가 올바르지 않습니다';
			return;
		}
		try {
			await api.post('/auth/email/verify-email', { token });
			status = 'success';
		} catch (err: unknown) {
			status = 'error';
			errorMessage = err instanceof Error ? err.message : '인증에 실패했습니다';
		}
	});
</script>

<svelte:head>
	<title>이메일 인증 - 모아오더</title>
</svelte:head>

<main class="flex min-h-screen items-center justify-center bg-background px-6 py-8">
	<div class="w-full max-w-sm space-y-6 text-center">
		<a href="/auth/login" class="inline-block text-4xl font-black leading-none tracking-[-0.05em] text-primary">
			moaorder
		</a>

		{#if status === 'loading'}
			<div class="flex flex-col items-center gap-3">
				<div class="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
				<p class="text-[13px] text-muted-foreground">인증 중...</p>
			</div>
		{:else if status === 'success'}
			<div class="space-y-5">
				<div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100">
					<svg class="size-9 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
					</svg>
				</div>
				<div class="space-y-2">
					<h2 class="text-[22px] font-bold tracking-[-0.03em] text-foreground">이메일 인증 완료</h2>
					<p class="text-[14px] leading-relaxed text-muted-foreground">이메일 인증이 성공적으로 완료됐어요.</p>
				</div>
				<button
					onclick={() => goto('/')}
					class="flex h-12 w-full items-center justify-center rounded-xl bg-primary px-5 text-[14px] font-bold text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99]"
				>
					홈으로 이동
				</button>
			</div>
		{:else}
			<div class="space-y-5">
				<div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
					<svg class="size-9 text-destructive" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
					</svg>
				</div>
				<div class="space-y-2">
					<h2 class="text-[22px] font-bold tracking-[-0.03em] text-foreground">인증 실패</h2>
					<p class="text-[14px] leading-relaxed text-muted-foreground">{errorMessage}</p>
				</div>
				<a
					href="/auth/email/login"
					class="flex h-12 w-full items-center justify-center rounded-xl border border-border bg-background px-5 text-[14px] font-bold text-foreground transition-colors hover:bg-muted"
				>
					로그인으로 돌아가기
				</a>
			</div>
		{/if}
	</div>
</main>
