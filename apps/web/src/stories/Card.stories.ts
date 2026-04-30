import type { Meta, StoryObj } from '@storybook/sveltekit';
import Card from '$lib/components/ui/card/card.svelte';

const meta = {
	title: '컴포넌트/Card',
	component: Card,
	tags: ['autodocs'],
	argTypes: {
		size: {
			control: 'radio',
			options: ['default', 'sm'],
			description: '카드 크기 (패딩)',
		},
	},
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const 기본카드: Story = {
	args: { size: 'default' },
	render: (args) => ({
		Component: Card,
		props: args,
		slots: {
			default: `
				<div style="padding:0 1.5rem;">
					<h3 style="font-size:1rem;font-weight:600;margin-bottom:4px;">신선한 제주 감귤 공동구매</h3>
					<p style="font-size:0.875rem;color:var(--muted-foreground);">마감까지 2일 남았습니다</p>
				</div>
			`,
		},
	}),
};

export const 소형카드: Story = {
	args: { size: 'sm' },
	render: (args) => ({
		Component: Card,
		props: args,
		slots: {
			default: `
				<div style="padding:0 1rem;">
					<p style="font-size:0.875rem;font-weight:500;">참여자: 12명</p>
					<p style="font-size:0.75rem;color:var(--muted-foreground);">목표: 30명</p>
				</div>
			`,
		},
	}),
};

export const 공구카드: Story = {
	render: () => ({
		Component: Card,
		slots: {
			default: `
				<img src="https://placehold.co/400x200/EC4445/ffffff?text=공동구매" alt="공동구매 이미지" style="width:100%;" />
				<div style="padding:0 1.5rem;">
					<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
						<h3 style="font-size:1rem;font-weight:700;">유기농 사과 10kg</h3>
						<span style="background:var(--primary);color:var(--primary-foreground);border-radius:999px;padding:2px 8px;font-size:11px;font-weight:500;">진행중</span>
					</div>
					<p style="font-size:0.875rem;color:var(--muted-foreground);margin-bottom:12px;">참여자 18 / 30명 · 마감 D-3</p>
					<p style="font-size:1.125rem;font-weight:700;color:var(--primary);">35,000원</p>
				</div>
			`,
		},
	}),
};
