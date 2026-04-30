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
				<div class="h-10 w-10 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
				<p class="text-sm text-muted-foreground">인증 중...</p>
			</div>
		{:else if status === 'success'}
			<div class="space-y-4">
				<div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
					<svg class="size-8 text-green-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
					</svg>
				</div>
				<div>
					<h2 class="text-xl font-bold">이메일 인증 완료!</h2>
					<p class="mt-1 text-sm text-muted-foreground">이메일 인증이 성공적으로 완료되었습니다.</p>
				</div>
				<button
					onclick={() => goto('/')}
					class="flex h-12 w-full items-center justify-center rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground hover:brightness-95 active:scale-[0.99]"
				>
					홈으로 이동
				</button>
			</div>
		{:else}
			<div class="space-y-4">
				<div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
					<svg class="size-8 text-red-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
					</svg>
				</div>
				<div>
					<h2 class="text-xl font-bold">인증 실패</h2>
					<p class="mt-1 text-sm text-muted-foreground">{errorMessage}</p>
				</div>
				<a
					href="/auth/email/login"
					class="flex h-12 w-full items-center justify-center rounded-xl border border-border bg-background px-5 text-sm font-semibold hover:bg-muted"
				>
					로그인으로 돌아가기
				</a>
			</div>
		{/if}
	</div>
</main>
