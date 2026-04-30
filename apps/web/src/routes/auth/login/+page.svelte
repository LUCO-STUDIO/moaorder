<script lang="ts">
	import { HugeiconsIcon } from '@hugeicons/svelte';
	import { Mail01Icon } from '@hugeicons/core-free-icons';

	const KAKAO_CLIENT_ID = import.meta.env.VITE_KAKAO_CLIENT_ID ?? '';
	const REDIRECT_URI = `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/kakao/callback`;

	function handleKakaoLogin() {
		const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code`;
		window.location.href = kakaoAuthUrl;
	}
</script>

<svelte:head>
	<title>로그인 - 모아오더</title>
</svelte:head>

<!-- Header: desktop only — wordmark with BAND-style subtle drop shadow -->
<header
	class="relative z-10 hidden h-[52px] items-center justify-center bg-background shadow-[0_1px_1px_0_rgba(0,0,0,0.08)] sm:flex"
>
	<a
		href="/auth/login"
		class="text-[28px] font-black leading-none tracking-[-0.05em] text-foreground"
	>
		moaorder
	</a>
</header>

<main class="bg-background px-10 pt-[38px] pb-8 sm:px-8">
	<div class="mx-auto w-full space-y-[30px] sm:max-w-[360px]">
		<!-- Title -->
		<h1 class="text-center text-[25px] font-medium leading-tight text-foreground sm:text-[32px]">
			로그인
		</h1>

		<!-- CTA buttons -->
		<div class="space-y-3">
			<button
				onclick={handleKakaoLogin}
				class="relative flex w-full cursor-pointer items-center justify-center rounded-[12px] bg-[#FEE500] h-12 px-5 text-[17px] font-medium transition-all hover:brightness-95 active:scale-[0.99]"
				style="color: rgba(0, 0, 0, 0.85);"
			>
				<svg class="absolute left-5 size-6" viewBox="0 0 18 18" fill="none" aria-hidden="true">
					<path
						d="M9 0.75C4.30547 0.75 0.5 3.7125 0.5 7.36875C0.5 9.84375 2.06719 12.0094 4.41875 13.1719L3.51875 16.4844C3.43906 16.7766 3.78125 17.0156 4.04531 16.8422L7.99844 14.225C8.32812 14.2563 8.66172 14.275 9 14.275C13.6938 14.275 17.5 11.3125 17.5 7.65625C17.5 4 13.6945 0.75 9 0.75Z"
						fill="#000000"
					/>
				</svg>
				<span>카카오로 시작</span>
			</button>

			<a
				href="/auth/email/login"
				class="relative flex w-full items-center justify-center rounded-[12px] bg-primary h-12 px-5 text-[17px] font-medium text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99]"
			>
				<HugeiconsIcon icon={Mail01Icon} size={24} class="absolute left-5" />
				<span>이메일로 시작</span>
			</a>
		</div>
	</div>
</main>
