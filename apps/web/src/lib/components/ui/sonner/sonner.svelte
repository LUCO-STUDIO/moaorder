<script lang="ts">
	import { Toaster as Sonner, type ToasterProps as SonnerProps } from "svelte-sonner";
	import { mode } from "mode-watcher";
	import { HugeiconsIcon } from '@hugeicons/svelte';
	import {
		Loading03Icon,
		CheckmarkCircleIcon,
		OctagonXIcon,
		InformationCircleIcon,
		DangerIcon
	} from '@hugeicons/core-free-icons';

	let { ...restProps }: SonnerProps = $props();
</script>

<Sonner
	theme={mode.current}
	class="toaster group"
	style="--normal-bg: var(--color-popover); --normal-text: var(--color-popover-foreground); --normal-border: var(--color-border);"
	{...restProps}
>
	{#snippet loadingIcon()}
		<HugeiconsIcon icon={Loading03Icon} size={16} class="animate-spin" />
	{/snippet}
	{#snippet successIcon()}
		<HugeiconsIcon icon={CheckmarkCircleIcon} size={16} />
	{/snippet}
	{#snippet errorIcon()}
		<HugeiconsIcon icon={OctagonXIcon} size={16} />
	{/snippet}
	{#snippet infoIcon()}
		<HugeiconsIcon icon={InformationCircleIcon} size={16} />
	{/snippet}
	{#snippet warningIcon()}
		<HugeiconsIcon icon={DangerIcon} size={16} />
	{/snippet}
</Sonner>
