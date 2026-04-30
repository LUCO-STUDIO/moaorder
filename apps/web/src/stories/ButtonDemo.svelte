<script lang="ts">
	import Button from '$lib/components/ui/button/button.svelte';
	import type { ButtonProps } from '$lib/components/ui/button/button.svelte';

	type Props = ButtonProps & { label?: string };

	let { label = '버튼', ...rest }: Props = $props();
</script>

<Button {...rest}>{label}</Button>
