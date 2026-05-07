<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { tick } from 'svelte';
	import { api } from '$lib/api';
	import { setUser } from '$lib/stores/auth';
	import type { AuthUser } from '$lib/stores/auth';
	import { toast } from 'svelte-sonner';
	import { handleApiError } from '$lib/error-handler';
	import {
		IconEye,
		IconEyeOff,
		IconShieldX,
		IconAlertTriangleFilled,
		IconShieldHalfFilled,
		IconShieldCheckFilled,
		IconCircleCheck,
		IconCircleCheckFilled,
		IconCheck
	} from '@tabler/icons-svelte';
	import { Popover, PopoverTrigger, PopoverContent } from '$lib/components/ui/popover';
	import { Calendar } from '$lib/components/ui/calendar';
	import { CalendarDate, getLocalTimeZone, today, type DateValue } from '@internationalized/date';
	import termsText from '$lib/legal/terms.txt?raw';

	type Step = 'fields' | 'consents';
	let step = $state<Step>(page.url.searchParams.get('step') === 'consents' ? 'consents' : 'fields');

	let email = $state(page.url.searchParams.get('email') ?? '');
	let password = $state('');
	let name = $state('');
	let birthdate = $state(''); // YYYYMMDD (8 digits)
	let birthdateValue = $state<DateValue | undefined>(undefined);
	let birthdatePopoverOpen = $state(false);
	let loading = $state(false);
	let showPassword = $state(false);

	const todayDate = today(getLocalTimeZone());
	const minDate = new CalendarDate(1900, 1, 1);

	$effect(() => {
		if (birthdateValue) {
			const y = birthdateValue.year.toString().padStart(4, '0');
			const m = birthdateValue.month.toString().padStart(2, '0');
			const d = birthdateValue.day.toString().padStart(2, '0');
			birthdate = `${y}${m}${d}`;
		}
	});

	const displayBirthdate = $derived(
		birthdate.length === 8
			? `${birthdate.slice(0, 4)}.${birthdate.slice(4, 6)}.${birthdate.slice(6, 8)}`
			: ''
	);

	let emailError = $state('');
	let passwordError = $state('');
	let nameError = $state('');
	let birthdateError = $state('');

	// Consents
	let agreeTerms = $state(false);
	let agreePrivacy = $state(false);
	let consentError = $state('');

	let allRequired = $derived(agreeTerms);
	let agreeAll = $derived(allRequired && agreePrivacy);

	// Age 14+ derived from birthdate (PIPA §22-2)
	const isAge14Plus = $derived(() => {
		if (!birthdateValue) return false;
		const t = todayDate;
		let age = t.year - birthdateValue.year;
		const beforeBirthday =
			t.month < birthdateValue.month ||
			(t.month === birthdateValue.month && t.day < birthdateValue.day);
		if (beforeBirthday) age--;
		return age >= 14;
	});

	const isEmailValid = $derived(
		/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)
	);
	const isPasswordValid = $derived(
		password.length >= 8 &&
			password.length <= 16 &&
			/(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};:'",.<>/?\\|`~])/.test(password)
	);
	const isNameValid = $derived(name.trim().length > 0);
	const isBirthdateValid = $derived(/^\d{8}$/.test(birthdate));
	const isStep1Valid = $derived(
		isEmailValid && isPasswordValid && isNameValid && isBirthdateValid
	);

	type PasswordStrength = 'unusable' | 'weak' | 'medium' | 'safe';
	const passwordStrength = $derived<PasswordStrength | null>(
		password.length === 0 ? null : computeStrength(password)
	);

	function computeStrength(pw: string): PasswordStrength {
		const lengthOk = pw.length >= 8 && pw.length <= 16;
		const hasLetter = /[A-Za-z]/.test(pw);
		const hasNumber = /\d/.test(pw);
		const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};:'",.<>/?\\|`~]/.test(pw);
		if (!lengthOk || !hasLetter || !hasNumber || !hasSpecial) return 'unusable';
		const hasUpper = /[A-Z]/.test(pw);
		const hasLower = /[a-z]/.test(pw);
		let score = 0;
		if (hasUpper) score++;
		if (hasLower) score++;
		if (hasNumber) score++;
		if (hasSpecial) score++;
		if (pw.length >= 12) score++;
		if (pw.length >= 14) score++;
		if (score >= 6) return 'safe';
		if (score >= 5) return 'medium';
		return 'weak';
	}

	const strengthLabel: Record<PasswordStrength, string> = {
		unusable: '사용불가',
		weak: '위험',
		medium: '보통',
		safe: '안전'
	};
	const strengthBadgeClass: Record<PasswordStrength, string> = {
		unusable: 'bg-destructive/10 text-destructive',
		weak: 'bg-orange-500/10 text-orange-600',
		medium: 'bg-amber-500/10 text-amber-600',
		safe: 'bg-emerald-500/10 text-emerald-600'
	};
	const strengthIcon = {
		unusable: IconShieldX,
		weak: IconAlertTriangleFilled,
		medium: IconShieldHalfFilled,
		safe: IconShieldCheckFilled
	} as const;

	let emailInput: HTMLInputElement | null = $state(null);

	function toggleAll() {
		const next = !agreeAll;
		agreeTerms = next;
		agreePrivacy = next;
	}

	function downloadTerms() {
		const blob = new Blob([termsText.trim()], { type: 'text/plain;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = '모아오더_이용약관.txt';
		a.click();
		URL.revokeObjectURL(url);
	}

	const termsBlocks = termsText
		.trim()
		.split(/\n\s*\n/)
		.map((block) => {
			const lines = block.split('\n');
			return { header: lines[0], body: lines.slice(1) };
		});

	function validateFields(): boolean {
		emailError = '';
		passwordError = '';
		nameError = '';
		birthdateError = '';
		let ok = true;

		if (!email || !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)) {
			emailError = '유효한 이메일 주소를 입력해주세요';
			ok = false;
		}
		if (password.length < 8 || password.length > 16) {
			passwordError = '비밀번호는 8~16자여야 합니다';
			ok = false;
		} else if (!/(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};:'",.<>/?\\|`~])/.test(password)) {
			passwordError = '영문, 숫자, 특수문자를 모두 포함해야 합니다';
			ok = false;
		}
		if (!name.trim()) {
			nameError = '이름을 입력해주세요';
			ok = false;
		}
		if (!/^\d{8}$/.test(birthdate)) {
			birthdateError = '생년월일 8자리를 입력해주세요 (예: 19900101)';
			ok = false;
		} else if (!isAge14Plus()) {
			birthdateError = '만 14세 이상만 가입할 수 있어요';
			ok = false;
		}
		return ok;
	}

	async function handleNext() {
		if (!validateFields()) return;
		step = 'consents';
		await tick();
		window.scrollTo({ top: 0 });
	}

	async function handleBack() {
		step = 'fields';
		await tick();
		window.scrollTo({ top: 0 });
	}

	async function handleSubmit() {
		consentError = '';
		if (!allRequired) {
			consentError = '필수 항목에 모두 동의해주세요';
			return;
		}
		loading = true;
		try {
			// Backend currently accepts: email, password, nickname
			// TODO: extend to send name, birthdate, consents (marketing) once API supports
			await api.post('/auth/email/signup', { email, password, nickname: name.trim() });
			const me = await api.get<AuthUser>('/auth/me');
			setUser(me);
			toast.success('회원가입이 완료됐어요. 이메일 인증 링크를 확인해주세요.');
			if (me.role === 'owner') {
				goto('/owner');
			} else {
				goto('/');
			}
		} catch (err: unknown) {
			handleApiError(err, { fallbackTitle: '회원가입 실패' });
		} finally {
			loading = false;
		}
	}

	const inputClass =
		'flex h-11 w-full appearance-none items-center border-0 border-b border-input bg-transparent px-0 py-0 text-[22px] font-light leading-none tracking-[-0.22px] placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50';
	const submitClass =
		'relative flex h-12 w-full cursor-pointer items-center justify-center rounded-xl bg-primary px-5 text-[17px] font-medium text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100';
</script>

<svelte:head>
	<title>회원가입 - 모아오더</title>
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
	<div class="mx-auto w-full space-y-[40px] sm:max-w-[360px]">
		<!-- Title -->
		<div class="text-center">
			<h1 class="text-[25px] font-medium leading-tight text-foreground sm:text-[32px]">
				회원가입
			</h1>
			{#if step === 'consents'}
				<p class="mt-[11px] text-sm text-muted-foreground">서비스 이용을 위한 안내를 확인하세요.</p>
			{:else if email}
				<p class="mt-0.5 text-[23px] font-light text-muted-foreground">{email}</p>
			{/if}
		</div>

		{#if step === 'fields'}
			<form
				onsubmit={(e) => { e.preventDefault(); handleNext(); }}
				class="space-y-[34px]"
			>
				<div class="space-y-[40px]">
					{#if emailError}
						<p class="text-xs text-destructive text-center">{emailError}</p>
					{/if}

					<!-- Password -->
					<div class="relative space-y-1.5">
						<input
							id="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							oninput={(e) => {
								const filtered = e.currentTarget.value.replace(/[^\x20-\x7E]/g, '');
								if (filtered !== e.currentTarget.value) {
									e.currentTarget.value = filtered;
									password = filtered;
								}
							}}
							placeholder="비밀번호"
							autocomplete="new-password"
							aria-label="비밀번호"
							lang="en"
							inputmode="text"
							class="{inputClass} pr-32"
							disabled={loading}
						/>
						{#if passwordStrength}
							{@const StrengthIcon = strengthIcon[passwordStrength]}
							<span
								aria-live="polite"
								class="pointer-events-none absolute top-1/2 right-10 flex -translate-y-1/2 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold {strengthBadgeClass[passwordStrength]}"
							>
								<StrengthIcon size={12} />
								{strengthLabel[passwordStrength]}
							</span>
						{/if}
						{#if password.length > 0}
							<button
								type="button"
								onclick={() => (showPassword = !showPassword)}
								aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 표시'}
								class="absolute top-1/2 right-0 flex size-9 -translate-y-1/2 cursor-pointer items-center justify-center text-muted-foreground/60 transition-colors hover:text-foreground"
							>
								{#if showPassword}
									<IconEyeOff size={20} stroke={1.5} />
								{:else}
									<IconEye size={20} stroke={1.5} />
								{/if}
							</button>
						{/if}
						<p class="pointer-events-none absolute top-full left-0 mt-1.5 text-xs text-muted-foreground/60">
							8~16자 영문 대소문자, 숫자, 특수문자를 사용하세요.
						</p>
						{#if passwordError}
							<p class="text-xs text-destructive">{passwordError}</p>
						{/if}
					</div>

					<!-- Name -->
					<div class="space-y-1.5">
						<input
							id="name"
							type="text"
							bind:value={name}
							onkeydown={(e) => {
								if (e.key === 'Tab' && !e.shiftKey) birthdatePopoverOpen = true;
							}}
							placeholder="이름"
							autocomplete="name"
							aria-label="이름"
							class={inputClass}
							disabled={loading}
						/>
						{#if nameError}
							<p class="text-xs text-destructive">{nameError}</p>
						{/if}
					</div>

					<!-- Birthdate -->
					<div class="space-y-1.5">
						<Popover bind:open={birthdatePopoverOpen}>
							<PopoverTrigger
								aria-label="생년월일 선택"
								disabled={loading}
								class="{inputClass} cursor-pointer items-center text-left {displayBirthdate ? 'text-foreground' : 'text-muted-foreground/40'}"
							>
								{displayBirthdate || '생년월일'}
							</PopoverTrigger>
							<PopoverContent class="w-auto p-0" align="start">
								<Calendar
									type="single"
									bind:value={birthdateValue}
									locale="ko-KR"
									captionLayout="dropdown"
									maxValue={todayDate}
									minValue={minDate}
									onValueChange={() => (birthdatePopoverOpen = false)}
								/>
							</PopoverContent>
						</Popover>
						{#if birthdateError}
							<p class="text-xs text-destructive">{birthdateError}</p>
						{/if}
					</div>
				</div>

				<button type="submit" disabled={loading || !isStep1Valid} class={submitClass}>
					확인
				</button>
			</form>
		{:else}
			<form
				onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}
				class="space-y-[40px]"
			>
				<!-- Consents card (BAND style) -->
				<div class="space-y-[11px] rounded-[16px] border border-border bg-card p-5">
					<button
						type="button"
						onclick={toggleAll}
						class="flex w-full cursor-pointer items-center gap-3 text-left"
					>
						{#if agreeAll}
							<IconCircleCheckFilled size={24} class="text-primary" />
						{:else}
							<IconCircleCheck size={24} class="text-muted-foreground/20" />
						{/if}
						<span class="text-[15px] text-foreground">
							<span class="font-bold">전체동의</span>
							<span class="text-muted-foreground"> (선택 항목 포함)</span>
						</span>
					</button>

					<div class="space-y-3">
						<label class="flex cursor-pointer items-center gap-3">
							<input type="checkbox" bind:checked={agreeTerms} class="sr-only" />
							{#if agreeTerms}
								<IconCircleCheckFilled size={24} class="text-primary" />
							{:else}
								<IconCircleCheck size={24} class="text-muted-foreground/20" />
							{/if}
							<span class="text-[15px] text-foreground">
								이용약관 동의 <span class="text-muted-foreground">(필수)</span>
							</span>
						</label>
						<div class="max-h-40 space-y-3 overflow-y-auto bg-muted/30 px-4 py-3 text-[12px] leading-relaxed text-muted-foreground">
							{#each termsBlocks as block}
								<div>
									{#if block.body.length > 0}
										<p class="font-semibold text-foreground">{block.header}</p>
										{#each block.body as line}
											{#if line.startsWith('- ')}
												<p class="pl-3">{line}</p>
											{:else}
												<p>{line}</p>
											{/if}
										{/each}
									{:else}
										<p>{block.header}</p>
									{/if}
								</div>
							{/each}
							<div class="flex justify-end pt-2">
								<button
									type="button"
									onclick={downloadTerms}
									class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
								>
									다운로드
								</button>
							</div>
						</div>
					</div>

					<div class="space-y-3">
						<label class="flex cursor-pointer items-center justify-between gap-3">
							<div class="flex items-center gap-3">
								<input type="checkbox" bind:checked={agreePrivacy} class="sr-only" />
								{#if agreePrivacy}
									<IconCircleCheckFilled size={24} class="text-primary" />
								{:else}
									<IconCircleCheck size={24} class="text-muted-foreground/20" />
								{/if}
								<span class="text-[15px] text-foreground">
									개인정보 수집 및 이용 동의 <span class="text-muted-foreground">(선택)</span>
								</span>
							</div>
							<a
								href="/legal/privacy"
								target="_blank"
								rel="noreferrer"
								class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
							>
								보기
							</a>
						</label>
						<div class="flex items-center gap-3 pl-9">
							<IconCheck
								size={16}
								stroke={2.5}
								class={agreePrivacy ? 'text-primary' : 'text-muted-foreground/30'}
							/>
							<span class="text-[13px] text-muted-foreground">
								이벤트, 광고성 정보 안내 (선택)
							</span>
						</div>
					</div>

					{#if consentError}
						<p class="pt-1 text-xs text-destructive">{consentError}</p>
					{/if}
				</div>

				<button type="submit" disabled={loading || !allRequired} aria-busy={loading} class={submitClass}>
					<span class={loading ? 'invisible' : ''}>확인</span>
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
