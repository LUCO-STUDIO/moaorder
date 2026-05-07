<script lang="ts">
	import { Toaster as Sonner, type ToasterProps as SonnerProps } from "svelte-sonner";
	import { mode } from "mode-watcher";
	import {
		IconLoader2,
		IconCircleCheck,
		IconAlertOctagonFilled,
		IconInfoCircle,
		IconAlertTriangleFilled
	} from '@tabler/icons-svelte';

	let { ...restProps }: SonnerProps = $props();
</script>

<Sonner
	theme={mode.current}
	class="toaster group"
	style="--normal-bg: var(--color-popover); --normal-text: var(--color-popover-foreground); --normal-border: var(--color-border);"
	{...restProps}
>
	{#snippet loadingIcon()}
		<IconLoader2 size={16} class="animate-spin" />
	{/snippet}
	{#snippet successIcon()}
		<IconCircleCheck size={16} />
	{/snippet}
	{#snippet errorIcon()}
		<IconAlertOctagonFilled size={16} />
	{/snippet}
	{#snippet infoIcon()}
		<IconInfoCircle size={16} />
	{/snippet}
	{#snippet warningIcon()}
		<IconAlertTriangleFilled size={16} />
	{/snippet}
</Sonner>
