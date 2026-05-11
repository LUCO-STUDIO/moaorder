<script lang="ts">
	import { goto } from '$app/navigation';
	import { IconEye, IconEyeOff } from '@tabler/icons-svelte';
	import { api } from '$lib/api';
	import { setUser } from '$lib/stores/auth';
	import type { AuthUser } from '$lib/stores/auth';
	import { handleApiError } from '$lib/error-handler';

	const KAKAO_CLIENT_ID = import.meta.env.VITE_KAKAO_CLIENT_ID ?? '';
	const REDIRECT_URI = `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/kakao/callback`;

	let email = $state('');
	let password = $state('');
	let showPassword = $state(false);
	let loading = $state(false);
	let errorMessage = $state('');

	const isEmailValid = $derived(
		/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)
	);
	const canSubmit = $derived(isEmailValid && password.length > 0 && !loading);

	function handleKakaoLogin() {
		const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code`;
		window.location.href = kakaoAuthUrl;
	}

	async function handleLogin() {
		errorMessage = '';
		if (!canSubmit) return;
		loading = true;
		try {
			await api.post('/auth/email/login', { email, password });
			const me = await api.get<AuthUser>('/auth/me');
			setUser(me);
			goto('/');
		} catch (err: unknown) {
			const status = (err as { status?: number })?.status;
			if (status === 401 || status === 404) {
				errorMessage = '이메일 또는 비밀번호가 일치하지 않아요.';
			} else {
				handleApiError(err, { fallbackTitle: '로그인 실패' });
			}
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>로그인 - 모아오더</title>
</svelte:head>

<div class="flex min-h-screen flex-col bg-background">
	<main class="flex flex-1 items-center justify-center px-4 sm:px-6">
		<div class="w-full max-w-xs sm:max-w-sm">
			<a
				href="/"
				class="mb-6 inline-block text-4xl font-black leading-none tracking-tight text-primary"
			>
				moaorder
			</a>

			<div class="space-y-6 sm:space-y-8">
			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleLogin();
				}}
				class="space-y-3"
			>
				<input
					type="email"
					bind:value={email}
					placeholder="이메일"
					autocomplete="email"
					disabled={loading}
					aria-label="이메일"
					class="h-11 w-full rounded-lg border border-input bg-background px-4 text-sm placeholder:text-muted-foreground/60 hover:border-primary/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50 sm:h-12 sm:text-base"
				/>

				<div class="relative">
					<input
						type={showPassword ? 'text' : 'password'}
						bind:value={password}
						placeholder="비밀번호"
						autocomplete="current-password"
						disabled={loading}
						aria-label="비밀번호"
						class="h-11 w-full rounded-lg border border-input bg-background px-4 pr-11 text-sm placeholder:text-muted-foreground/60 hover:border-primary/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50 sm:h-12 sm:pr-12 sm:text-base"
					/>
					<button
						type="button"
						onclick={() => (showPassword = !showPassword)}
						aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
						class="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
					>
						{#if showPassword}
							<IconEye class="size-5" />
						{:else}
							<IconEyeOff class="size-5" />
						{/if}
					</button>
				</div>

				{#if errorMessage}
					<p class="text-xs text-destructive sm:text-sm">{errorMessage}</p>
				{/if}

				<button
					type="submit"
					disabled={!canSubmit}
					aria-busy={loading}
					class="relative flex h-11 w-full cursor-pointer items-center justify-center rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100 sm:h-12 sm:text-base"
				>
					<span class={loading ? 'invisible' : ''}>로그인</span>
					{#if loading}
						<span class="absolute inset-0 flex items-center justify-center gap-1.5" aria-hidden="true">
							<span class="size-2 animate-bounce rounded-full bg-current [animation-delay:-0.3s]"></span>
							<span class="size-2 animate-bounce rounded-full bg-current [animation-delay:-0.15s]"></span>
							<span class="size-2 animate-bounce rounded-full bg-current"></span>
						</span>
					{/if}
				</button>
			</form>

			<div class="flex items-center gap-3 text-xs text-muted-foreground">
				<span class="h-px flex-1 bg-border"></span>
				<span>또는</span>
				<span class="h-px flex-1 bg-border"></span>
			</div>

			<button
				onclick={handleKakaoLogin}
				class="relative flex h-11 w-full cursor-pointer items-center justify-center rounded-lg bg-[#FEE500] px-5 text-sm font-medium transition-all hover:brightness-95 active:scale-[0.99] sm:h-12 sm:text-base"
				style="color: rgba(0, 0, 0, 0.85);"
			>
				<svg class="absolute left-5 size-5" viewBox="0 0 18 18" fill="none" aria-hidden="true">
					<path
						d="M9 0.75C4.30547 0.75 0.5 3.7125 0.5 7.36875C0.5 9.84375 2.06719 12.0094 4.41875 13.1719L3.51875 16.4844C3.43906 16.7766 3.78125 17.0156 4.04531 16.8422L7.99844 14.225C8.32812 14.2563 8.66172 14.275 9 14.275C13.6938 14.275 17.5 11.3125 17.5 7.65625C17.5 4 13.6945 0.75 9 0.75Z"
						fill="#000000"
					/>
				</svg>
				카카오로 시작
			</button>

			<div class="flex items-center justify-center gap-3 text-xs text-muted-foreground sm:text-sm">
				<a href="/auth/email/signup" class="transition-colors hover:text-foreground">회원가입</a>
				<span class="text-border">·</span>
				<a href="/auth/email/forgot" class="transition-colors hover:text-foreground">비밀번호 찾기</a>
			</div>
			</div>
		</div>
	</main>

	<footer class="px-4 pb-6 pt-4 text-center text-xs text-muted-foreground sm:px-6">
		<a href="/legal/terms" class="hover:text-foreground">이용약관</a>
		<span class="mx-2 text-border">|</span>
		<a href="/legal/privacy" class="hover:text-foreground">개인정보처리방침</a>
	</footer>
</div>
