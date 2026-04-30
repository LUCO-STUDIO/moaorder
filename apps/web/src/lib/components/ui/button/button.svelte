<script lang="ts" module>
	import { cn, type WithElementRef } from "$lib/utils.js";
	import type { HTMLAnchorAttributes, HTMLButtonAttributes } from "svelte/elements";
	import { type VariantProps, tv } from "tailwind-variants";

	export const buttonVariants = tv({
		base: "focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:aria-invalid:border-destructive/50 rounded-md border border-transparent bg-clip-padding text-sm font-medium focus-visible:ring-3 active:not-aria-[haspopup]:translate-y-px aria-invalid:ring-3 [&_svg:not([class*='size-'])]:size-4 group/button inline-flex shrink-0 items-center justify-center whitespace-nowrap transition-all outline-none select-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
		variants: {
			variant: {
				default: "bg-primary text-primary-foreground hover:bg-primary/80",
				outline: "border-border bg-background hover:bg-muted hover:text-foreground dark:bg-input/30 dark:border-input dark:hover:bg-input/50 aria-expanded:bg-muted aria-expanded:text-foreground shadow-xs",
				secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 aria-expanded:bg-secondary aria-expanded:text-secondary-foreground",
				ghost: "hover:bg-muted hover:text-foreground dark:hover:bg-muted/50 aria-expanded:bg-muted aria-expanded:text-foreground",
				destructive: "bg-destructive/10 hover:bg-destructive/20 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/20 text-destructive focus-visible:border-destructive/40 dark:hover:bg-destructive/30",
				link: "text-primary underline-offset-4 hover:underline",
			},
			size: {
				default: "h-11 gap-1.5 px-4 text-sm in-data-[slot=button-group]:rounded-md has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
				xs: "h-7 gap-1 rounded-[min(var(--radius-md),8px)] px-2 text-xs in-data-[slot=button-group]:rounded-md has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
				sm: "h-9 gap-1 rounded-[min(var(--radius-md),10px)] px-3 text-sm in-data-[slot=button-group]:rounded-md has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
				lg: "h-[3.25rem] gap-2 rounded-xl px-6 text-base font-semibold has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4",
				icon: "size-11",
				"icon-xs": "size-7 rounded-[min(var(--radius-md),8px)] in-data-[slot=button-group]:rounded-md [&_svg:not([class*='size-'])]:size-3",
				"icon-sm": "size-9 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-md",
				"icon-lg": "size-[3.25rem] rounded-xl",
			},
		},
		defaultVariants: {
			variant: "default",
			size: "default",
		},
	});

	export type ButtonVariant = VariantProps<typeof buttonVariants>["variant"];
	export type ButtonSize = VariantProps<typeof buttonVariants>["size"];

	export type SpinnerVariant = "ring" | "dots" | "bars";

	export type ButtonProps = WithElementRef<HTMLButtonAttributes> &
		WithElementRef<HTMLAnchorAttributes> & {
			variant?: ButtonVariant;
			size?: ButtonSize;
			/** When true, hides children and shows a spinner centered in the button (Toss TDS pattern). */
			loading?: boolean;
			/** Spinner shape when loading. Defaults to "ring". */
			spinner?: SpinnerVariant;
		};
</script>

<script lang="ts">
	let {
		class: className,
		variant = "default",
		size = "default",
		ref = $bindable(null),
		href = undefined,
		type = "button",
		disabled,
		loading = false,
		spinner: spinnerVariant = "dots",
		children,
		...restProps
	}: ButtonProps = $props();

	const isDisabled = $derived(disabled || loading);
</script>

{#snippet spinnerRing()}
	<svg class="size-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
		<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-opacity="0.25" />
		<path
			fill="currentColor"
			d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
		/>
	</svg>
{/snippet}

{#snippet spinnerDots()}
	<span class="inline-flex items-center gap-1" aria-hidden="true">
		<span class="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.3s]"></span>
		<span class="size-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.15s]"></span>
		<span class="size-1.5 animate-bounce rounded-full bg-current"></span>
	</span>
{/snippet}

{#snippet spinnerBars()}
	<span class="inline-flex items-end gap-0.5" aria-hidden="true">
		<span class="h-3 w-0.5 animate-pulse rounded-full bg-current [animation-delay:-0.4s]"></span>
		<span class="h-4 w-0.5 animate-pulse rounded-full bg-current [animation-delay:-0.2s]"></span>
		<span class="h-3 w-0.5 animate-pulse rounded-full bg-current"></span>
	</span>
{/snippet}

{#snippet spinner()}
	{#if spinnerVariant === "dots"}{@render spinnerDots()}{:else if spinnerVariant === "bars"}{@render spinnerBars()}{:else}{@render spinnerRing()}{/if}
{/snippet}

{#if href}
	<a
		bind:this={ref}
		data-slot="button"
		class={cn("relative", buttonVariants({ variant, size }), className)}
		href={isDisabled ? undefined : href}
		aria-disabled={isDisabled}
		aria-busy={loading}
		role={isDisabled ? "link" : undefined}
		tabindex={isDisabled ? -1 : undefined}
		{...restProps}
	>
		<span class={loading ? "invisible" : "contents"}>
			{@render children?.()}
		</span>
		{#if loading}
			<span class="absolute inset-0 flex items-center justify-center">
				{@render spinner()}
			</span>
		{/if}
	</a>
{:else}
	<button
		bind:this={ref}
		data-slot="button"
		class={cn("relative", buttonVariants({ variant, size }), className)}
		{type}
		disabled={isDisabled}
		aria-busy={loading}
		{...restProps}
	>
		<span class={loading ? "invisible" : "contents"}>
			{@render children?.()}
		</span>
		{#if loading}
			<span class="absolute inset-0 flex items-center justify-center">
				{@render spinner()}
			</span>
		{/if}
	</button>
{/if}
