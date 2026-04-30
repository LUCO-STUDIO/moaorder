<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount, tick } from 'svelte';
	import { api } from '$lib/api';
	import { setUser } from '$lib/stores/auth';
	import type { AuthUser } from '$lib/stores/auth';
	import { handleApiError } from '$lib/error-handler';
	import {
		Drawer,
		DrawerContent,
		DrawerHeader,
		DrawerTitle,
		DrawerDescription
	} from '$lib/components/ui/drawer';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogDescription
	} from '$lib/components/ui/dialog';

	type Step = 'email' | 'password';

	let step = $state<Step>('email');
	let email = $state('');
	let password = $state('');
	let loading = $state(false);
	let emailError = $state('');
	let passwordError = $state('');
	let showSignupSheet = $state(false);

	let emailInput: HTMLInputElement | null = $state(null);
	let passwordInput: HTMLInputElement | null = $state(null);

	// Responsive: dialog on md+, sheet on mobile (Tailwind md = 768px)
	let isDesktop = $state(false);

	onMount(() => {
		const mq = window.matchMedia('(min-width: 768px)');
		isDesktop = mq.matches;
		const handler = (e: MediaQueryListEvent) => (isDesktop = e.matches);
		mq.addEventListener('change', handler);
		return () => mq.removeEventListener('change', handler);
	});

	const isEmailValid = $derived(
		/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)
	);
	const isPasswordFilled = $derived(password.length > 0);

	async function handleNext() {
		emailError = '';
		if (!isEmailValid) {
			emailError = '유효한 이메일 주소를 입력해주세요';
			return;
		}
		loading = true;
		try {
			const res = await api.post<{ exists: boolean }>('/auth/email/check-email', { email });
			if (res.exists) {
				step = 'password';
				await tick();
				passwordInput?.focus();
			} else {
				showSignupSheet = true;
			}
		} catch (err: unknown) {
			handleApiError(err, { fallbackTitle: '이메일 확인 실패' });
		} finally {
			loading = false;
		}
	}

	async function handleBack() {
		step = 'email';
		password = '';
		passwordError = '';
		await tick();
		emailInput?.focus();
	}

	const headerTitle = $derived(step === 'email' ? '이메일로 시작' : '비밀번호 입력');

	function goToSignup() {
		goto(`/auth/email/signup?email=${encodeURIComponent(email)}`);
	}

	async function handleLogin() {
		passwordError = '';
		if (!isPasswordFilled) {
			passwordError = '비밀번호를 입력해주세요';
			return;
		}
		loading = true;
		try {
			await api.post<{ user_id: string; role: string; email_verified: boolean }>(
				'/auth/email/login',
				{ email, password }
			);
			const me = await api.get<AuthUser>('/auth/me');
			setUser(me);
			if (me.role === 'owner') {
				goto('/owner');
			} else {
				goto('/');
			}
		} catch (err: unknown) {
			handleApiError(err, { fallbackTitle: '로그인 실패' });
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>이메일로 시작 - 모아오더</title>
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
	<div class="mx-auto w-full space-y-[63px] sm:max-w-[360px]">
		<!-- Title (responsive: mobile 25px, desktop 32px) -->
		<h1
			class="text-center text-[25px] font-medium leading-tight text-foreground sm:text-[32px]"
		>
			{headerTitle}
		</h1>

		<!-- Step: Email -->
		{#if step === 'email'}
			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleNext();
				}}
				class="space-y-[34px]"
			>
				<div class="space-y-1.5">
					<input
						bind:this={emailInput}
						id="email"
						type="email"
						bind:value={email}
						placeholder="이메일"
						autocomplete="email"
						autofocus
						disabled={loading}
						aria-label="이메일"
						class="flex h-12 w-full border-0 border-b border-input bg-transparent px-0 pt-0 pb-[10px] text-[24px] font-light tracking-[-0.27px] placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50"
					/>
					{#if emailError}
						<p class="text-xs text-destructive">{emailError}</p>
					{/if}
				</div>

				<button
					type="submit"
					disabled={!isEmailValid || loading}
					aria-busy={loading}
					class="relative flex h-12 w-full cursor-pointer items-center justify-center rounded-xl bg-primary px-5 text-[17px] font-medium text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100"
				>
					<span class={loading ? 'invisible' : ''}>다음</span>
					{#if loading}
						<span class="absolute inset-0 flex items-center justify-center gap-1.5" aria-hidden="true">
							<span class="size-2 animate-bounce rounded-full bg-current [animation-delay:-0.3s]"></span>
							<span class="size-2 animate-bounce rounded-full bg-current [animation-delay:-0.15s]"></span>
							<span class="size-2 animate-bounce rounded-full bg-current"></span>
						</span>
					{/if}
				</button>
			</form>
		{/if}

		<!-- Step: Password -->
		{#if step === 'password'}
			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleLogin();
				}}
				class="space-y-4"
			>
				<!-- Email summary + change link -->
				<div class="flex items-center justify-between rounded-lg bg-muted px-3 py-2.5">
					<div class="min-w-0">
						<p class="text-[11px] text-muted-foreground">이메일</p>
						<p class="truncate text-sm font-medium text-foreground">{email}</p>
					</div>
					<button
						type="button"
						onclick={handleBack}
						class="ml-3 shrink-0 cursor-pointer text-xs font-semibold text-primary underline underline-offset-2"
					>
						변경
					</button>
				</div>

				<div class="space-y-1.5">
					<label for="password" class="text-sm font-medium text-muted-foreground">비밀번호</label>
					<input
						bind:this={passwordInput}
						id="password"
						type="password"
						bind:value={password}
						placeholder="••••••••"
						autocomplete="current-password"
						class="flex h-12 w-full border-0 border-b border-input bg-transparent px-0 py-2 text-base placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50 sm:text-sm"
						disabled={loading}
					/>
					{#if passwordError}
						<p class="text-xs text-destructive">{passwordError}</p>
					{/if}
				</div>

				<div class="flex justify-end">
					<a
						href="/auth/email/forgot"
						class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
					>
						비밀번호를 잊으셨나요?
					</a>
				</div>

				<button
					type="submit"
					disabled={loading || !isPasswordFilled}
					aria-busy={loading}
					class="relative flex h-12 w-full cursor-pointer items-center justify-center rounded-xl bg-primary px-5 text-[17px] font-medium text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100"
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
		{/if}
	</div>
</main>

<!-- Responsive: Dialog (modal) on desktop, Sheet (bottom sheet) on mobile -->
{#snippet signupPromptBody()}
	<div class="mt-6 space-y-0.5 pb-0">
		<button
			type="button"
			onclick={goToSignup}
			class="flex h-12 w-full cursor-pointer items-center justify-center rounded-xl bg-primary px-5 text-base font-bold text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99]"
		>
			회원가입하기
		</button>
		<button
			type="button"
			onclick={() => (showSignupSheet = false)}
			class="flex h-12 w-full cursor-pointer items-center justify-center px-5 text-base font-semibold text-muted-foreground transition-colors hover:text-foreground"
		>
			취소
		</button>
	</div>
{/snippet}

{#if isDesktop}
	<Dialog bind:open={showSignupSheet}>
		<DialogContent class="sm:max-w-md !pb-2" showCloseButton={false}>
			<DialogHeader>
				<DialogTitle class="text-2xl font-bold leading-snug">가입할 수 있는 이메일이에요</DialogTitle>
				<DialogDescription class="pt-1.5 text-[15px] leading-relaxed">
					{email} 으로 가입하고 모아오더를 시작해보세요.
				</DialogDescription>
			</DialogHeader>
			{@render signupPromptBody()}
		</DialogContent>
	</Dialog>
{:else}
	<Drawer bind:open={showSignupSheet}>
		<DrawerContent
			class="!inset-x-3 !bottom-[max(0.75rem,env(safe-area-inset-bottom))] !mt-0 !rounded-2xl !border-0 pb-2 shadow-xl"
		>
			<DrawerHeader class="!text-left">
				<DrawerTitle class="text-xl font-bold leading-snug">가입할 수 있는 이메일이에요</DrawerTitle>
				<DrawerDescription class="pt-1.5 text-[15px] leading-relaxed">
					{email} 으로 가입하고 모아오더를 시작해보세요.
				</DrawerDescription>
			</DrawerHeader>
			<div class="px-4">
				{@render signupPromptBody()}
			</div>
		</DrawerContent>
	</Drawer>
{/if}
