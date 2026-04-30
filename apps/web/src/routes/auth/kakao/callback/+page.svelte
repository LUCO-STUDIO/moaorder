<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { fetchMe } from '$lib/stores/auth';

	let error = $state('');

	onMount(async () => {
		const code = page.url.searchParams.get('code');
		if (!code) {
			error = '인증 코드가 없습니다';
			return;
		}

		try {
			const result = await api.post<{ user_id: string; role: string; is_new: boolean }>(
				'/auth/kakao/exchange',
				{ code }
			);

			const user = await fetchMe();
			if (!user) {
				error = '사용자 정보를 가져올 수 없습니다';
				return;
			}

			if (result.is_new) {
				goto('/onboarding/customer');
				return;
			}

			if (user.role === 'owner') {
				goto('/owner');
			} else {
				goto('/');
			}
		} catch (err) {
			error = '로그인에 실패했습니다. 다시 시도해주세요.';
		}
	});
</script>

<svelte:head>
	<title>로그인 중... - 모아오더</title>
</svelte:head>

<main class="flex min-h-screen items-center justify-center bg-gray-50">
	{#if error}
		<div class="text-center space-y-4">
			<p class="text-red-500">{error}</p>
			<a href="/auth/login" class="text-sm text-primary hover:underline">다시 로그인하기</a>
		</div>
	{:else}
		<div class="text-center space-y-2">
			<div class="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
			<p class="text-sm text-gray-500">로그인 처리 중...</p>
		</div>
	{/if}
</main>
