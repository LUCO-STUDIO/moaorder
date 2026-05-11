<script lang="ts">
	import { onMount } from 'svelte';
	import { IconMailFilled } from '@tabler/icons-svelte';

	const KAKAO_CLIENT_ID = import.meta.env.VITE_KAKAO_CLIENT_ID ?? '';
	const REDIRECT_URI = `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/kakao/callback`;
	const LAST_METHOD_KEY = 'moaorder:last_login_method';

	type LoginMethod = 'email' | 'kakao';

	let lastLoginMethod = $state<LoginMethod | null>(null);

	onMount(() => {
		const last = localStorage.getItem(LAST_METHOD_KEY);
		if (last === 'email' || last === 'kakao') {
			lastLoginMethod = last;
		}
	});

	function handleKakaoLogin() {
		localStorage.setItem(LAST_METHOD_KEY, 'kakao');
		const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code`;
		window.location.href = kakaoAuthUrl;
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
				class="mb-6 inline-block text-4xl font-black leading-none tracking-tight text-primary transition-all hover:opacity-80 active:scale-[0.98]"
			>
				moaorder
			</a>

			<div class="space-y-6 sm:space-y-8">
				<div class="space-y-2">
					{#if lastLoginMethod === 'email'}
						<div class="flex justify-end pr-4">
							<div class="relative rounded-md bg-foreground px-3 py-1.5 text-xs text-background">
								마지막으로 로그인한 수단이에요
								<span class="absolute -bottom-1 right-6 size-2 rotate-45 bg-foreground"></span>
							</div>
						</div>
					{/if}

					<a
						href="/auth/email/login"
						class="relative flex h-11 w-full items-center justify-center rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] sm:h-12 sm:text-base"
					>
						<IconMailFilled class="absolute left-5 size-5" />
						이메일로 시작
					</a>
				</div>

				<div class="space-y-3">
					{#if lastLoginMethod === 'kakao'}
						<div class="flex justify-center">
							<div class="relative rounded-md bg-foreground px-3 py-1.5 text-xs text-background">
								마지막으로 로그인한 수단이에요
								<span class="absolute -bottom-1 left-1/2 size-2 -translate-x-1/2 rotate-45 bg-foreground"></span>
							</div>
						</div>
					{/if}

					<div class="flex justify-center gap-3">
						<button
							onclick={handleKakaoLogin}
							aria-label="카카오로 로그인"
							class="flex size-12 items-center justify-center rounded-full bg-[#FEE500] transition-all hover:brightness-95 active:scale-95 sm:size-14"
						>
							<svg class="size-6" viewBox="0 0 18 18" fill="none" aria-hidden="true">
								<path
									d="M9 0.75C4.30547 0.75 0.5 3.7125 0.5 7.36875C0.5 9.84375 2.06719 12.0094 4.41875 13.1719L3.51875 16.4844C3.43906 16.7766 3.78125 17.0156 4.04531 16.8422L7.99844 14.225C8.32812 14.2563 8.66172 14.275 9 14.275C13.6938 14.275 17.5 11.3125 17.5 7.65625C17.5 4 13.6945 0.75 9 0.75Z"
									fill="#000000"
								/>
							</svg>
						</button>
					</div>
				</div>

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
