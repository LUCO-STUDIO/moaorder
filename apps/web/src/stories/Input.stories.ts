import type { Meta, StoryObj } from '@storybook/sveltekit';
import Input from '$lib/components/ui/input/input.svelte';

const meta = {
	title: '컴포넌트/Input',
	component: Input,
	tags: ['autodocs'],
	argTypes: {
		placeholder: { control: 'text', description: '플레이스홀더 텍스트' },
		disabled: { control: 'boolean', description: '비활성화 상태' },
		'aria-invalid': { control: 'boolean', description: '오류 상태' },
		type: {
			control: 'select',
			options: ['text', 'email', 'password', 'number', 'tel'],
			description: '입력 타입',
		},
	},
	args: {
		disabled: false,
	},
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const 기본: Story = {
	args: {
		placeholder: '이름을 입력하세요',
		type: 'text',
	},
};

export const 이메일: Story = {
	args: {
		placeholder: 'example@moaorder.com',
		type: 'email',
	},
};

export const 비밀번호: Story = {
	args: {
		placeholder: '비밀번호를 입력하세요',
		type: 'password',
	},
};

export const 값있음: Story = {
	args: {
		value: '홍길동',
		type: 'text',
	},
};

export const 오류상태: Story = {
	args: {
		placeholder: '이메일을 입력하세요',
		'aria-invalid': true,
		type: 'email',
	},
};

export const 비활성화: Story = {
	args: {
		placeholder: '수정 불가',
		disabled: true,
		value: '변경할 수 없는 값',
	},
};
