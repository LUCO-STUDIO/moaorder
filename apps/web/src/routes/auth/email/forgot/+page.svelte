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
			<div class="space-y-5 text-center">
				<div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
					<svg class="size-9 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect width="20" height="16" x="2" y="4" rx="2"/>
						<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
					</svg>
				</div>
				<div class="space-y-2">
					<h2 class="text-[22px] font-bold tracking-[-0.03em] text-foreground">이메일을 확인해주세요</h2>
					<p class="text-[14px] leading-relaxed text-muted-foreground">
						해당 이메일로 가입된 계정이 있다면<br />비밀번호 재설정 링크를 보내드렸어요.
					</p>
				</div>
				<a
					href="/auth/email/login"
					class="flex h-12 w-full items-center justify-center rounded-xl border border-border bg-background px-5 text-[14px] font-bold text-foreground transition-colors hover:bg-muted"
				>
					로그인으로 돌아가기
				</a>
			</div>
		{:else}
			<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-5">
				<p class="text-[14px] leading-relaxed text-muted-foreground">
					가입한 이메일 주소를 입력하시면<br />비밀번호 재설정 링크를 보내드릴게요.
				</p>

				<div class="space-y-2">
					<label for="email" class="text-[13px] font-bold text-foreground">이메일</label>
					<input
						id="email"
						type="email"
						bind:value={email}
						placeholder="name@example.com"
						autocomplete="email"
						class="flex h-12 w-full rounded-xl border border-input bg-background px-4 text-[14px] placeholder:text-muted-foreground focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
						disabled={loading}
					/>
					{#if emailError}
						<p class="text-[12px] font-semibold text-destructive">{emailError}</p>
					{/if}
				</div>

				<button
					type="submit"
					disabled={loading}
					class="flex h-12 w-full items-center justify-center rounded-xl bg-primary px-5 text-[14px] font-bold text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:opacity-50"
				>
					{loading ? '전송 중...' : '재설정 링크 보내기'}
				</button>

				<a
					href="/auth/email/login"
					class="flex w-full items-center justify-center text-[13px] font-semibold text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
				>
					로그인으로 돌아가기
				</a>
			</form>
		{/if}
	</div>
</main>
