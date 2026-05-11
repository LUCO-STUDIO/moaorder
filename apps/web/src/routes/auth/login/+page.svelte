<script lang="ts">
	import { onMount } from 'svelte';
	import { IconArrowLeft, IconMailFilled } from '@tabler/icons-svelte';
	import { toast } from 'svelte-sonner';

	const KAKAO_CLIENT_ID = import.meta.env.VITE_KAKAO_CLIENT_ID ?? '';
	const REDIRECT_URI = `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/kakao/callback`;
	const LAST_METHOD_KEY = 'moaorder:last_login_method';

	type LoginMethod = 'email' | 'kakao' | 'naver' | 'google';

	let lastLoginMethod = $state<LoginMethod | null>(null);

	onMount(() => {
		const last = localStorage.getItem(LAST_METHOD_KEY);
		if (
			last === 'email' ||
			last === 'kakao' ||
			last === 'naver' ||
			last === 'google'
		) {
			lastLoginMethod = last;
		}
	});

	function handleKakaoLogin() {
		localStorage.setItem(LAST_METHOD_KEY, 'kakao');
		const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code`;
		window.location.href = kakaoAuthUrl;
	}

	function handleSocialPending(label: string) {
		toast.info(`${label} 로그인은 준비 중이에요`);
	}
</script>

<svelte:head>
	<title>로그인 - 모아오더</title>
</svelte:head>

<div class="flex min-h-screen flex-col bg-background">
	<main class="flex flex-1 items-center justify-center px-4 sm:px-6">
		<div class="w-full max-w-xs sm:max-w-sm">
			<div class="mb-9 text-center">
				<a
					href="/"
					class="inline-block text-5xl font-black leading-none tracking-tight text-primary transition-all hover:opacity-80 active:scale-[0.98]"
				>
					moaorder
				</a>
				<p class="mt-4 text-base font-semibold leading-snug text-muted-foreground sm:text-2xl">
					동네 가게 공구 소식부터 단골 혜택까지<br />
					한 곳에서 편하게 모아봐요
				</p>
			</div>

			<div class="space-y-6 sm:space-y-8">
				<div class="space-y-2">
					{#if lastLoginMethod === 'email'}
						<div class="flex justify-end pr-4">
							<div class="relative rounded-md bg-foreground px-3.5 py-2 text-[13px] font-medium text-background">
								마지막으로 로그인한 수단이에요
								<span class="absolute -bottom-2 right-6 h-0 w-0 border-x-[5px] border-t-[8px] border-x-transparent border-t-foreground"></span>
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

				<div class="!mt-14 flex justify-center gap-5">
					<div class="relative">
						{#if lastLoginMethod === 'kakao'}
							<div class="absolute -top-11 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-foreground px-3.5 py-2 text-[13px] font-medium text-background">
								마지막으로 로그인한 수단이에요
								<span class="absolute -bottom-2 left-1/2 h-0 w-0 -translate-x-1/2 border-x-[5px] border-t-[8px] border-x-transparent border-t-foreground"></span>
							</div>
						{/if}
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

					<div class="relative">
						{#if lastLoginMethod === 'naver'}
							<div class="absolute -top-11 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-foreground px-3.5 py-2 text-[13px] font-medium text-background">
								마지막으로 로그인한 수단이에요
								<span class="absolute -bottom-2 left-1/2 h-0 w-0 -translate-x-1/2 border-x-[5px] border-t-[8px] border-x-transparent border-t-foreground"></span>
							</div>
						{/if}
						<button
							onclick={() => handleSocialPending('네이버')}
							aria-label="네이버로 로그인"
							class="flex size-12 items-center justify-center rounded-full bg-[#03C75A] transition-all hover:brightness-95 active:scale-95 sm:size-14"
						>
							<svg class="size-6" viewBox="0 0 16 16" fill="none" aria-hidden="true">
								<path
									d="M9.79 8.36 5.81 2H1.6v12h4.37V7.64L9.95 14h4.45V2H9.79v6.36z"
									fill="#FFFFFF"
								/>
							</svg>
						</button>
					</div>

					<div class="relative">
						{#if lastLoginMethod === 'google'}
							<div class="absolute -top-11 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-foreground px-3.5 py-2 text-[13px] font-medium text-background">
								마지막으로 로그인한 수단이에요
								<span class="absolute -bottom-2 left-1/2 h-0 w-0 -translate-x-1/2 border-x-[5px] border-t-[8px] border-x-transparent border-t-foreground"></span>
							</div>
						{/if}
						<button
							onclick={() => handleSocialPending('구글')}
							aria-label="구글로 로그인"
							class="flex size-12 items-center justify-center rounded-full bg-white ring-1 ring-border transition-all hover:brightness-95 active:scale-95 sm:size-14"
						>
							<svg class="size-6" viewBox="0 0 48 48" aria-hidden="true">
								<path
									fill="#FFC107"
									d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
								/>
								<path
									fill="#FF3D00"
									d="m6.306 14.691 6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
								/>
								<path
									fill="#4CAF50"
									d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
								/>
								<path
									fill="#1976D2"
									d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571.001-.001.002-.001.003-.002l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"
								/>
							</svg>
						</button>
					</div>
				</div>

				<div class="!mt-2 text-center">
					<a
						href="/auth/email/forgot"
						class="text-xs text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
					>
						로그인에 어려움을 겪고 계신가요?
					</a>
				</div>
			</div>
		</div>
	</main>

	<footer class="flex items-center justify-between border-t border-border px-4 py-4 text-xs text-muted-foreground sm:px-6">
		<a
			href="/"
			class="inline-flex items-center gap-1 rounded-lg bg-muted px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-muted/70 sm:text-sm"
		>
			<IconArrowLeft class="size-4" />
			홈페이지로 이동하기
		</a>
		<div class="flex items-center gap-2 text-xs sm:text-[13px]">
			<a href="/legal/terms" class="transition-colors hover:text-foreground">이용약관</a>
			<span class="text-border">|</span>
			<a href="/legal/privacy" class="transition-colors hover:text-foreground">개인정보처리방침</a>
		</div>
	</footer>
</div>
