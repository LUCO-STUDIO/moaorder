<script lang="ts">
	import { IconMailFilled } from '@tabler/icons-svelte';

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

<div class="flex min-h-screen flex-col bg-background">
	<main class="flex flex-1 items-center justify-center px-6">
		<div class="w-full max-w-[360px] space-y-10">
			<a href="/" class="inline-block text-[34px] font-black leading-none tracking-[-0.05em] text-primary">
				moaorder
			</a>

			<div class="space-y-2.5">
				<button
					onclick={handleKakaoLogin}
					class="relative flex h-12 w-full cursor-pointer items-center justify-center rounded-[12px] bg-[#FEE500] px-5 text-[15px] font-medium transition-all hover:brightness-95 active:scale-[0.99]"
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

				<a
					href="/auth/email/login"
					class="relative flex h-12 w-full items-center justify-center rounded-[12px] bg-foreground px-5 text-[15px] font-medium text-background transition-all hover:brightness-110 active:scale-[0.99]"
				>
					<IconMailFilled size={20} class="absolute left-5" />
					이메일로 시작
				</a>
			</div>

			<div class="flex items-center justify-center gap-3 text-[13px] text-muted-foreground">
				<a href="/auth/email/signup" class="transition-colors hover:text-foreground">회원가입</a>
				<span class="text-border">·</span>
				<a href="/auth/email/forgot" class="transition-colors hover:text-foreground">비밀번호 찾기</a>
			</div>
		</div>
	</main>

	<footer class="px-6 pb-6 pt-4 text-center text-[12px] text-muted-foreground">
		<a href="/legal/terms" class="hover:text-foreground">이용약관</a>
		<span class="mx-2 text-border">|</span>
		<a href="/legal/privacy" class="hover:text-foreground">개인정보처리방침</a>
	</footer>
</div>
