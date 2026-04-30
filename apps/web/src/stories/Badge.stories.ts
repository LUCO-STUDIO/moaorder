import type { Meta, StoryObj } from '@storybook/sveltekit';
import Badge from '$lib/components/ui/badge/badge.svelte';

const meta = {
	title: '컴포넌트/Badge',
	component: Badge,
	tags: ['autodocs'],
	argTypes: {
		variant: {
			control: 'select',
			options: ['default', 'secondary', 'destructive', 'outline', 'ghost', 'link'],
			description: '배지 스타일 변형',
		},
	},
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const 기본: Story = {
	args: { variant: 'default' },
	render: (args) => ({
		Component: Badge,
		props: args,
		slots: { default: '진행중' },
	}),
};

export const 보조: Story = {
	args: { variant: 'secondary' },
	render: (args) => ({
		Component: Badge,
		props: args,
		slots: { default: '마감임박' },
	}),
};

export const 위험: Story = {
	args: { variant: 'destructive' },
	render: (args) => ({
		Component: Badge,
		props: args,
		slots: { default: '마감' },
	}),
};

export const 외곽선: Story = {
	args: { variant: 'outline' },
	render: (args) => ({
		Component: Badge,
		props: args,
		slots: { default: '신규' },
	}),
};

export const 유령: Story = {
	args: { variant: 'ghost' },
	render: (args) => ({
		Component: Badge,
		props: args,
		slots: { default: '준비중' },
	}),
};

export const 모든변형: Story = {
	render: () => ({
		Component: Badge,
		slots: { default: '샘플' },
	}),
	decorators: [
		() => ({
			template: `
				<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
					<span data-slot="badge" style="background:var(--primary);color:var(--primary-foreground);border-radius:999px;padding:2px 8px;font-size:12px;font-weight:500;">진행중</span>
					<span data-slot="badge" style="background:var(--secondary);color:var(--secondary-foreground);border-radius:999px;padding:2px 8px;font-size:12px;font-weight:500;">마감임박</span>
					<span data-slot="badge" style="background:oklch(0.577 0.245 27.325 / 0.1);color:var(--destructive);border-radius:999px;padding:2px 8px;font-size:12px;font-weight:500;">마감</span>
					<span data-slot="badge" style="border:1px solid var(--border);color:var(--foreground);border-radius:999px;padding:2px 8px;font-size:12px;font-weight:500;">신규</span>
				</div>
			`,
		}),
	],
};
