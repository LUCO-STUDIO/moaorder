<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { handleApiError } from '$lib/error-handler';

	const initialEmail = page.url.searchParams.get('email') ?? '';

	let sessionToken = $state('');
	let codeDigits = $state<string[]>(['', '', '', '', '', '']);
	let codeError = $state('');
	let loading = $state(false);
	let resending = $state(false);
	let resendCooldown = $state(0);
	let cooldownInterval: ReturnType<typeof setInterval> | null = null;
	let inputs: (HTMLInputElement | null)[] = $state([null, null, null, null, null, null]);

	const code = $derived(codeDigits.join(''));
	const codeFilled = $derived(code.length === 6 && /^\d{6}$/.test(code));

	function startCooldown(seconds: number) {
		resendCooldown = seconds;
		if (cooldownInterval) clearInterval(cooldownInterval);
		cooldownInterval = setInterval(() => {
			resendCooldown -= 1;
			if (resendCooldown <= 0 && cooldownInterval) {
				clearInterval(cooldownInterval);
				cooldownInterval = null;
			}
		}, 1000);
	}

	async function sendCode() {
		if (!initialEmail) {
			goto('/auth/email/login');
			return;
		}
		resending = true;
		codeError = '';
		try {
			const res = await api.post<{ session_token: string; expires_in: number }>(
				'/auth/email/send-code',
				{ email: initialEmail }
			);
			sessionToken = res.session_token;
			startCooldown(60);
		} catch (err: unknown) {
			handleApiError(err, { fallbackTitle: '인증번호 발송 실패' });
		} finally {
			resending = false;
		}
	}

	onMount(() => {
		sendCode().then(() => tick()).then(() => inputs[0]?.focus());
		return () => {
			if (cooldownInterval) clearInterval(cooldownInterval);
		};
	});

	function handleDigitInput(idx: number, e: Event) {
		const value = (e.target as HTMLInputElement).value.replace(/\D/g, '');
		if (value.length > 1) {
			// User pasted: spread across cells.
			const chars = value.slice(0, 6).split('');
			for (let i = 0; i < 6; i++) codeDigits[i] = chars[i] ?? '';
			tick().then(() => {
				const last = Math.min(chars.length, 6) - 1;
				inputs[Math.min(last + 1, 5)]?.focus();
			});
			return;
		}
		codeDigits[idx] = value;
		if (value && idx < 5) inputs[idx + 1]?.focus();
	}

	function handleKeyDown(idx: number, e: KeyboardEvent) {
		if (e.key === 'Backspace' && !codeDigits[idx] && idx > 0) {
			inputs[idx - 1]?.focus();
		}
	}

	async function handleSubmit() {
		codeError = '';
		if (!codeFilled || !sessionToken) {
			codeError = '인증번호 6자리를 입력해주세요';
			return;
		}
		loading = true;
		try {
			const res = await api.post<{ verified_email_token: string }>(
				'/auth/email/verify-code',
				{ session_token: sessionToken, code }
			);
			const params = new URLSearchParams({
				email: initialEmail,
				verified_email_token: res.verified_email_token
			});
			goto(`/auth/email/signup?${params.toString()}`);
		} catch {
			codeError = '인증번호가 일치하지 않거나 만료되었어요';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>이메일 인증 - 모아오더</title>
</svelte:head>

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
	<div class="mx-auto w-full space-y-[40px] sm:max-w-[440px]">
		<div class="text-center">
			<h1 class="text-[25px] font-medium leading-tight text-foreground sm:text-[32px]">
				이메일 인증
			</h1>
			<p class="mt-[11px] text-sm text-muted-foreground">
				{initialEmail}으로 인증번호를 보냈어요. 6자리를 입력해주세요.
			</p>
		</div>

		<form
			onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}
			class="space-y-[24px]"
		>
			<div class="space-y-3">
				<div class="flex justify-between gap-2">
					{#each codeDigits as digit, i (i)}
						<input
							bind:this={inputs[i]}
							type="text"
							inputmode="numeric"
							autocomplete={i === 0 ? 'one-time-code' : 'off'}
							maxlength={i === 0 ? 6 : 1}
							value={digit}
							oninput={(e) => handleDigitInput(i, e)}
							onkeydown={(e) => handleKeyDown(i, e)}
							aria-label={`인증번호 ${i + 1}자리`}
							class="h-14 w-12 rounded-xl border border-input bg-transparent text-center text-[24px] font-medium tracking-[-0.27px] text-foreground placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50 sm:w-14"
							disabled={loading}
						/>
					{/each}
				</div>
				{#if codeError}
					<p class="text-xs text-destructive">{codeError}</p>
				{/if}
				<div class="flex items-center justify-between text-xs text-muted-foreground">
					<span>인증번호는 5분 후 만료됩니다.</span>
					<button
						type="button"
						onclick={sendCode}
						disabled={resending || resendCooldown > 0}
						class="cursor-pointer underline underline-offset-2 hover:text-foreground disabled:cursor-not-allowed disabled:no-underline disabled:opacity-50"
					>
						{#if resendCooldown > 0}
							재발송 ({resendCooldown}s)
						{:else if resending}
							발송 중...
						{:else}
							재발송
						{/if}
					</button>
				</div>
			</div>

			<button
				type="submit"
				disabled={loading || !codeFilled || !sessionToken}
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
	</div>
</main>
