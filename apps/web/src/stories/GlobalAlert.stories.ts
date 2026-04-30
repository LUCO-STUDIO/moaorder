import type { Meta, StoryObj } from '@storybook/sveltekit';
import GlobalAlertDemo from './GlobalAlertDemo.svelte';

const meta = {
	title: '패턴/GlobalAlert',
	component: GlobalAlertDemo,
	tags: ['autodocs'],
	parameters: {
		docs: {
			description: {
				component: `
**GlobalAlert**는 \`showAlert()\` / \`showConfirm()\` 함수로 전역적으로 알림 다이얼로그를 띄우는 패턴입니다.

\`\`\`ts
import { showAlert, showConfirm } from '$lib/stores/alert';

// 단순 알림
showAlert('저장되었습니다', '변경사항이 성공적으로 저장되었습니다.');

// 확인/취소 다이얼로그
showConfirm({
  title: '공구를 삭제하시겠어요?',
  description: '삭제하면 복구할 수 없습니다.',
  confirmText: '삭제',
  destructive: true,
  onConfirm: async () => {
    await deleteGroup(id);
  },
});
\`\`\`

레이아웃 루트(\`+layout.svelte\`)에 \`<GlobalAlert />\`를 한 번만 마운트하면 앱 어디서나 사용 가능합니다.
				`,
			},
		},
	},
} satisfies Meta<typeof GlobalAlertDemo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const 단순알림: Story = {
	args: {
		mode: 'alert',
	},
};

export const 확인다이얼로그: Story = {
	args: {
		mode: 'confirm',
	},
};

export const 위험확인: Story = {
	args: {
		mode: 'destructive',
	},
};
