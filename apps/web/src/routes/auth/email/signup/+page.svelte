<script lang="ts">
	import { goto, beforeNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount, tick } from 'svelte';
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
		IconCheck,
		IconChevronLeft
	} from '@tabler/icons-svelte';
	import { Popover, PopoverTrigger, PopoverContent } from '$lib/components/ui/popover';
	import { Calendar } from '$lib/components/ui/calendar';
	import { CalendarDate, getLocalTimeZone, today, type DateValue } from '@internationalized/date';
	import termsText from '$lib/legal/terms.txt?raw';
	import privacyText from '$lib/legal/privacy-collection.txt?raw';
	import { REGIONS } from '$lib/regions';

	type Step = 'password' | 'name' | 'birthdate' | 'region' | 'consents';
	const STEP_ORDER: Step[] = ['password', 'name', 'birthdate', 'region', 'consents'];
	let step = $state<Step>('password');
	const stepIndex = $derived(STEP_ORDER.indexOf(step));

	const email = page.url.searchParams.get('email') ?? '';
	const verifiedEmailToken = page.url.searchParams.get('verified_email_token') ?? '';

	let password = $state('');
	let name = $state('');
	let birthdate = $state(''); // YYYYMMDD (8 digits)
	let birthdateValue = $state<DateValue | undefined>(undefined);
	let birthdatePopoverOpen = $state(false);
	let region = $state('');
	let regionPickerOpen = $state(false);
	let regionSearch = $state('');
	const filteredRegions = $derived(
		regionSearch.trim() ? REGIONS.filter((r) => r.includes(regionSearch.trim())) : REGIONS
	);
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

	// Consents
	let agreeTerms = $state(false);
	let agreePrivacy = $state(false);
	let consentError = $state('');

	const allRequired = $derived(agreeTerms);
	const agreeAll = $derived(allRequired && agreePrivacy);

	// Age 14+ derived from birthdate (PIPA §22-2)
	const isAge14Plus = $derived(() => {
		if (!birthdateValue) return false;
		let age = todayDate.year - birthdateValue.year;
		const beforeBirthday =
			todayDate.month < birthdateValue.month ||
			(todayDate.month === birthdateValue.month && todayDate.day < birthdateValue.day);
		if (beforeBirthday) age--;
		return age >= 14;
	});

	const isPasswordValid = $derived(
		password.length >= 8 &&
			password.length <= 16 &&
			/(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};:'",.<>/?\\|`~])/.test(password)
	);
	const isNameValid = $derived(name.trim().length > 0);
	const isBirthdateValid = $derived(/^\d{8}$/.test(birthdate));
	const isRegionValid = $derived(region.length > 0);

	const canAdvance = $derived(() => {
		switch (step) {
			case 'password':
				return isPasswordValid;
			case 'name':
				return isNameValid;
			case 'birthdate':
				return isBirthdateValid && isAge14Plus();
			case 'region':
				return isRegionValid;
			case 'consents':
				return allRequired;
		}
	});

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

	let passwordInput: HTMLInputElement | null = $state(null);
	let nameInput: HTMLInputElement | null = $state(null);

	// Leave-confirm: warn the user before any navigation away from the signup
	// page if they have started filling the form. The verify-email step
	// regenerates a code on mount, so a back-button press silently invalidates
	// their progress.
	let submittedSuccessfully = $state(false);
	let leaveConfirmOpen = $state(false);
	let pendingLeaveAction: (() => void) | null = $state(null);

	const isDirty = $derived(
		!submittedSuccessfully &&
			(password.length > 0 ||
				name.trim().length > 0 ||
				birthdate.length > 0 ||
				region.length > 0 ||
				agreeTerms ||
				agreePrivacy)
	);

	beforeNavigate((nav) => {
		if (!isDirty) return;
		if (nav.to?.url.pathname === page.url.pathname) return;
		nav.cancel();
		pendingLeaveAction = () => {
			submittedSuccessfully = true;
			if (nav.to) goto(nav.to.url.toString());
		};
		leaveConfirmOpen = true;
	});

	onMount(() => {
		const handler = (e: BeforeUnloadEvent) => {
			if (!isDirty) return;
			e.preventDefault();
			e.returnValue = '';
		};
		window.addEventListener('beforeunload', handler);
		// focus password input on initial mount
		tick().then(() => passwordInput?.focus());
		return () => window.removeEventListener('beforeunload', handler);
	});

	function confirmLeave() {
		const action = pendingLeaveAction;
		pendingLeaveAction = null;
		leaveConfirmOpen = false;
		action?.();
	}

	function cancelLeave() {
		pendingLeaveAction = null;
		leaveConfirmOpen = false;
	}

	function toggleAll() {
		const next = !agreeAll;
		agreeTerms = next;
		agreePrivacy = next;
	}

	function downloadFile(content: string, filename: string) {
		const blob = new Blob([content.trim()], { type: 'text/plain;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		a.click();
		URL.revokeObjectURL(url);
	}

	function parseBlocks(text: string) {
		return text
			.trim()
			.split(/\n\s*\n/)
			.map((block) => {
				const lines = block.split('\n');
				return { header: lines[0], body: lines.slice(1) };
			});
	}

	const termsBlocks = parseBlocks(termsText);
	const privacyBlocks = parseBlocks(privacyText);

	async function goNext() {
		if (!canAdvance()) return;
		if (step === 'consents') {
			await handleSubmit();
			return;
		}
		const next = STEP_ORDER[stepIndex + 1];
		if (!next) return;
		step = next;
		await tick();
		focusForStep(step);
	}

	function goBack() {
		if (stepIndex > 0) {
			const prev = STEP_ORDER[stepIndex - 1];
			step = prev;
			tick().then(() => focusForStep(step));
			return;
		}
		// First step — leave the page entirely (will trigger leave-confirm if dirty).
		history.back();
	}

	function focusForStep(s: Step) {
		if (s === 'password') passwordInput?.focus();
		else if (s === 'name') nameInput?.focus();
	}

	async function handleSubmit() {
		consentError = '';
		if (!allRequired) {
			consentError = '필수 항목에 동의해주세요';
			return;
		}
		if (!verifiedEmailToken) {
			toast.error('이메일 인증 세션이 만료되었어요. 다시 진행해주세요.');
			submittedSuccessfully = true;
			goto(`/auth/email/verify-email?email=${encodeURIComponent(email)}`);
			return;
		}
		loading = true;
		try {
			await api.post('/auth/email/signup', {
				verified_email_token: verifiedEmailToken,
				password,
				nickname: name.trim(),
				region: region.trim()
			});
			const me = await api.get<AuthUser>('/auth/me');
			setUser(me);
			submittedSuccessfully = true;
			toast.success('회원가입이 완료됐어요!');
			goto('/');
		} catch (err: unknown) {
			handleApiError(err, { fallbackTitle: '회원가입 실패' });
		} finally {
			loading = false;
		}
	}

	const inputClass =
		'flex h-14 w-full appearance-none items-center border-0 border-b-2 border-input bg-transparent px-0 py-0 text-[26px] font-light leading-none tracking-[-0.27px] placeholder:text-muted-foreground/40 focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-50';
	const ctaClass =
		'relative flex h-14 w-full cursor-pointer items-center justify-center rounded-xl bg-primary px-5 text-[17px] font-bold text-primary-foreground transition-all hover:brightness-95 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100';

	const stepTitles: Record<Step, string> = {
		password: '비밀번호를 만들어 주세요',
		name: '이름을 알려 주세요',
		birthdate: '생년월일을 알려 주세요',
		region: '어느 동네인가요?',
		consents: '약관에 동의해 주세요'
	};
	const stepSubtitles: Record<Step, string> = {
		password: `${email} 계정으로 가입해요`,
		name: '주문 내역과 알림에 사용해요',
		birthdate: '만 14세 이상부터 가입할 수 있어요',
		region: '내 동네의 공동구매가 홈에 보여요',
		consents: '서비스 이용을 위한 안내를 확인하세요'
	};
</script>

<svelte:head>
	<title>회원가입 - 모아오더</title>
</svelte:head>

<!-- Top bar: back + progress -->
<header
	class="sticky top-0 z-10 flex h-14 items-center justify-between bg-background px-4 sm:h-[52px] sm:shadow-[0_1px_1px_0_rgba(0,0,0,0.08)] sm:px-6"
>
	<button
		type="button"
		onclick={goBack}
		aria-label="이전으로"
		class="flex size-10 cursor-pointer items-center justify-center -ml-2 text-foreground transition-colors hover:text-primary"
	>
		<IconChevronLeft size={26} stroke={2} />
	</button>
	<span class="text-xs font-medium text-muted-foreground">{stepIndex + 1} / {STEP_ORDER.length}</span>
</header>

<main class="bg-background px-6 pt-6 pb-8 sm:px-8">
	<div class="mx-auto w-full sm:max-w-[440px]">
		<div class="space-y-2">
			<h1 class="text-[26px] font-bold leading-snug text-foreground sm:text-[28px]">
				{stepTitles[step]}
			</h1>
			<p class="text-sm text-muted-foreground">{stepSubtitles[step]}</p>
		</div>

		<form
			onsubmit={(e) => {
				e.preventDefault();
				goNext();
			}}
			class="mt-10 space-y-8"
		>
			{#if step === 'password'}
				<div class="relative space-y-1.5">
					<input
						bind:this={passwordInput}
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
					<p class="pt-2 text-xs text-muted-foreground/60">
						8~16자 영문 대소문자, 숫자, 특수문자를 사용하세요.
					</p>
				</div>
			{:else if step === 'name'}
				<div class="space-y-1.5">
					<input
						bind:this={nameInput}
						id="name"
						type="text"
						bind:value={name}
						placeholder="이름"
						autocomplete="name"
						aria-label="이름"
						class={inputClass}
						disabled={loading}
					/>
				</div>
			{:else if step === 'birthdate'}
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
					{#if birthdate.length === 8 && !isAge14Plus()}
						<p class="text-xs text-destructive">만 14세 이상만 가입할 수 있어요</p>
					{/if}
				</div>
			{:else if step === 'region'}
				<div class="space-y-1.5">
					<button
						type="button"
						disabled={loading}
						onclick={() => (regionPickerOpen = true)}
						aria-label="동네 선택"
						class="{inputClass} cursor-pointer items-center text-left {region ? 'text-foreground' : 'text-muted-foreground/40'}"
					>
						{region || '동네 선택'}
					</button>
				</div>
			{:else if step === 'consents'}
				<div class="space-y-3">
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
							<div class="max-h-40 space-y-3 overflow-y-auto rounded-l-[12px] bg-muted/30 px-4 py-3 text-[12px] leading-relaxed text-muted-foreground">
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
										onclick={() => downloadFile(termsText, '모아오더_이용약관.txt')}
										class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
									>
										다운로드
									</button>
								</div>
							</div>
						</div>

						<div class="space-y-3">
							<label class="flex cursor-pointer items-center gap-3">
								<input type="checkbox" bind:checked={agreePrivacy} class="sr-only" />
								{#if agreePrivacy}
									<IconCircleCheckFilled size={24} class="text-primary" />
								{:else}
									<IconCircleCheck size={24} class="text-muted-foreground/20" />
								{/if}
								<span class="text-[15px] text-foreground">
									개인정보 수집 및 이용 동의 <span class="text-muted-foreground">(선택)</span>
								</span>
							</label>
							<label class="flex cursor-pointer items-center gap-3 pl-9">
								<input type="checkbox" bind:checked={agreePrivacy} class="sr-only" />
								<IconCheck
									size={16}
									stroke={2.5}
									class={agreePrivacy ? 'text-primary' : 'text-muted-foreground/30'}
								/>
								<span class="text-[13px] text-muted-foreground">
									이벤트, 광고성 정보 안내 (선택)
								</span>
							</label>
						</div>

						{#if consentError}
							<p class="pt-1 text-xs text-destructive">{consentError}</p>
						{/if}
					</div>

					<div class="space-y-3 rounded-[16px] border border-border bg-card p-5">
						<p class="text-[15px] font-bold text-foreground">개인정보 수집 및 이용 안내</p>
						<div class="max-h-40 space-y-3 overflow-y-auto rounded-l-[12px] bg-muted/30 px-4 py-3 text-[12px] leading-relaxed text-muted-foreground">
							{#each privacyBlocks as block}
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
									onclick={() => downloadFile(privacyText, '모아오더_개인정보_수집_및_이용_안내.txt')}
									class="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
								>
									다운로드
								</button>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<button
				type="submit"
				disabled={loading || !canAdvance()}
				aria-busy={loading}
				class={ctaClass}
			>
				<span class={loading ? 'invisible' : ''}>
					{step === 'consents' ? '가입 완료' : '다음'}
				</span>
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

<!-- Region picker -->
{#if regionPickerOpen}
	<div
		class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
		onclick={(e) => {
			if (e.target === e.currentTarget) regionPickerOpen = false;
		}}
		onkeydown={(e) => {
			if (e.key === 'Escape') regionPickerOpen = false;
		}}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
	>
		<div class="w-full max-w-md rounded-t-2xl bg-background p-5 sm:rounded-2xl">
			<div class="mb-3 flex items-center justify-between">
				<h3 class="text-base font-bold text-foreground">동네 선택</h3>
				<button
					type="button"
					onclick={() => (regionPickerOpen = false)}
					class="text-xs text-muted-foreground hover:text-foreground"
				>
					닫기
				</button>
			</div>
			<input
				type="search"
				bind:value={regionSearch}
				placeholder="동네 검색 (예: 강남, 성남)"
				class="mb-3 h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
			/>
			<ul class="max-h-[60vh] space-y-1 overflow-y-auto">
				{#if filteredRegions.length === 0}
					<li class="px-3 py-4 text-center text-xs text-muted-foreground">검색 결과가 없습니다.</li>
				{/if}
				{#each filteredRegions as r}
					<li>
						<button
							type="button"
							onclick={() => {
								region = r;
								regionPickerOpen = false;
								regionSearch = '';
							}}
							class="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted {r === region ? 'bg-primary/10 text-primary font-medium' : 'text-foreground'}"
						>
							{r}
							{#if r === region}
								<span class="text-xs">선택됨</span>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		</div>
	</div>
{/if}

<!-- Leave-confirm dialog -->
{#if leaveConfirmOpen}
	<div
		class="fixed inset-0 z-[60] flex items-end justify-center bg-black/50 sm:items-center"
		onclick={(e) => {
			if (e.target === e.currentTarget) cancelLeave();
		}}
		onkeydown={(e) => {
			if (e.key === 'Escape') cancelLeave();
		}}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
	>
		<div class="w-full max-w-sm rounded-t-2xl bg-background p-5 sm:rounded-2xl">
			<h3 class="mb-2 text-base font-bold text-foreground">정말 나가시겠어요?</h3>
			<p class="mb-5 text-sm leading-relaxed text-muted-foreground">
				지금 나가시면 입력하신 정보가 사라지고, 인증번호도 다시 받아야 해요.
			</p>
			<div class="flex gap-2">
				<button
					type="button"
					onclick={cancelLeave}
					class="flex-1 cursor-pointer rounded-xl border border-border bg-background px-4 py-3 text-sm font-medium text-foreground hover:bg-muted"
				>
					계속 작성
				</button>
				<button
					type="button"
					onclick={confirmLeave}
					class="flex-1 cursor-pointer rounded-xl bg-destructive px-4 py-3 text-sm font-bold text-destructive-foreground hover:brightness-95"
				>
					나가기
				</button>
			</div>
		</div>
	</div>
{/if}
