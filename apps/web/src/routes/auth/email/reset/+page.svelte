<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';

	let token = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let loading = $state(false);
	let success = $state(false);

	let passwordError = $state('');
	let confirmPasswordError = $state('');

	onMount(() => {
		token = page.url.searchParams.get('token') ?? '';
		if (!token) {
			toast.error('유효하지 않은 링크입니다');
		}
	});

	function validate(): boolean {
		passwordError = '';
		confirmPasswordError = '';
		let ok = true;
		if (newPassword.length < 8 || !/(?=.*[A-Za-z])(?=.*\d)/.test(newPassword)) {
			passwordError = '비밀번호는 8자 이상, 영문자와 숫자를 모두 포함해야 합니다';
			ok = false;
		}
		if (newPassword !== confirmPassword) {
			confirmPasswordError = '비밀번호가 일치하지 않습니다';
			ok = false;
		}
		return ok;
	}

	async function handleSubmit() {
		if (!token) {
			toast.error('유효하지 않은 링크입니다');
			return;
		}
		if (!validate()) return;
		loading = true;
		try {
			await api.post('/auth/email/reset-password', { token, new_password: newPassword });
			success = true;
			toast.success('비밀번호가 성공적으로 변경되었습니다');
		} catch (err: unknown) {
			const msg = err instanceof Error ? err.message : '비밀번호 재설정에 실패했습니다';
			toast.error(msg);
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>비밀번호 재설정 - 모아오더</title>
</svelte:head>

<main class="flex min-h-screen items-center justify-center bg-background px-6 py-8">
	<div class="w-full max-w-sm space-y-8">
		<div class="flex flex-col items-center gap-2 text-center">
			<a href="/auth/login" class="text-4xl font-black leading-none tracking-[-0.05em] text-primary">
				moaorder
			</a>
			<p class="text-sm font-medium text-muted-foreground">새 비밀번호 설정</p>
		</div>

		{#if success}
			<div class="space-y-4 text-center">
				<div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
					<svg class="size-8 text-green-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
					</svg>
				</div>
				<div>
					<h2 class="text-xl font-bold">비밀번호가 변경되었습니다</h2>
					<p class="mt-1 text-sm text-muted-foreground">새 비밀번호로 로그인해주세요.</p>
				</div>
				<button
					onclick={() => goto('/auth/email/login')}
					class="flex h-12 w-full items-center justify-center rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground hover:brightness-95 active:scale-[0.99]"
				>
					로그인하기
				</button>
			</div>
		{:else}
			<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-4">
				<div class="space-y-1.5">
					<label for="new-password" class="text-sm font-medium">새 비밀번호</label>
					<input
						id="new-password"
						type="password"
						bind:value={newPassword}
						placeholder="영문+숫자 8자 이상"
						autocomplete="new-password"
						class="flex h-11 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
						disabled={loading}
					/>
					{#if passwordError}
						<p class="text-xs text-destructive">{passwordError}</p>
					{/if}
				</div>

				<div class="space-y-1.5">
					<label for="confirm-password" class="text-sm font-medium">비밀번호 확인</label>
					<input
						id="confirm-password"
						type="password"
						bind:value={confirmPassword}
						placeholder="비밀번호를 다시 입력해주세요"
						autocomplete="new-password"
						class="flex h-11 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
						disabled={loading}
					/>
					{#if confirmPasswordError}
						<p class="text-xs text-destructive">{confirmPasswordError}</p>
					{/if}
				</div>

				<button
					type="submit"
					disabled={loading || !token}
					class="flex h-12 w-full items-center justify-center rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground hover:brightness-95 active:scale-[0.99] disabled:opacity-50"
				>
					{loading ? '변경 중...' : '비밀번호 변경'}
				</button>
			</form>
		{/if}
	</div>
</main>
