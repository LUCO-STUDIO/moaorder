<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, authLoading, fetchMe } from '$lib/stores/auth';

	onMount(async () => {
		const currentUser = await fetchMe();
		if (!currentUser) {
			goto('/auth/login');
			return;
		}
		goto('/home');
	});
</script>

<svelte:head>
	<title>모아오더</title>
</svelte:head>

{#if $authLoading}
	<div class="flex min-h-screen items-center justify-center bg-background">
		<div class="flex flex-col items-center gap-3">
			<div class="h-10 w-10 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
			<p class="text-sm text-muted-foreground">잠시만요...</p>
		</div>
	</div>
{/if}
