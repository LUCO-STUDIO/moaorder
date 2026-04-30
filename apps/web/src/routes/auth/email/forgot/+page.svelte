<script lang="ts">
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';

	let email = $state('');
	let loading = $state(false);
	let submitted = $state(false);
	let emailError = $state('');

	function validate(): boolean {
		emailError = '';
		if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
			emailError = '유효한 이메일 주소를 입력해주세요';
			return false;
		}
		return true;
	}

	async function handleSubmit() {
		if (!validate()) return;
		loading = true;
		try {
			await api.post('/auth/email/forgot-password', { email });
			submitted = true;
		} catch {
			// Always show success to avoid email enumeration
			submitted = true;
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>비밀번호 찾기 - 모아오더</title>
</svelte:head>

<main class="flex min-h-screen items-center justify-center bg-background px-6 py-8">
	<div class="w-full max-w-sm space-y-8">
		<div class="flex flex-col items-center gap-2 text-center">
			<a href="/auth/login" class="text-4xl font-black leading-none tracking-[-0.05em] text-primary">
				moaorder
			</a>
			<p class="text-sm font-medium text-muted-foreground">비밀번호 찾기</p>
		</div>

		{#if submitted}
			<div class="space-y-4 text-center">
				<div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
					<svg class="size-8 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect width="20" height="16" x="2" y="4" rx="2"/>
						<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
					</svg>
				</div>
				<div>
					<h2 class="text-xl font-bold">이메일을 확인해주세요</h2>
					<p class="mt-1 text-sm text-muted-foreground">
						해당 이메일로 가입된 계정이 있다면 비밀번호 재설정 링크를 보내드렸습니다.
					</p>
				</div>
				<a
					href="/auth/email/login"
					class="flex h-12 w-full items-center justify-center rounded-xl border border-border bg-background px-5 text-sm font-semibold hover:bg-muted"
				>
					로그인으로 돌아가기
				</a>
			</div>
		{:else}
			<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-4">
				<p class="text-sm text-muted-foreground">
					가입한 이메일 주소를 입력하시면 비밀번호 재설정 링크를 보내드립니다.
				</p>

				<div class="space-y-1.5">
					<label for="email" class="text-sm font-medium">이메일</label>
					<input
						id="email"
						type="email"
						bind:value={email}
						placeholder="name@example.com"
						autocomplete="email"
						class="flex h-11 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
						disabled={loading}
					/>
					{#if emailError}
						<p class="text-xs text-destructive">{emailError}</p>
					{/if}
				</div>

				<button
					type="submit"
					disabled={loading}
					class="flex h-12 w-full items-center justify-center rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground hover:brightness-95 active:scale-[0.99] disabled:opacity-50"
				>
					{loading ? '전송 중...' : '재설정 링크 보내기'}
				</button>

				<a
					href="/auth/email/login"
					class="flex w-full items-center justify-center text-sm text-muted-foreground underline underline-offset-2 hover:text-foreground"
				>
					로그인으로 돌아가기
				</a>
			</form>
		{/if}
	</div>
</main>
